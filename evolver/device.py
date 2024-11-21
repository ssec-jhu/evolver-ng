import logging
import time
from collections import defaultdict

from evolver.base import BaseInterface, ConfigDescriptor
from evolver.connection.interface import Connection
from evolver.controller.interface import Controller
from evolver.hardware.interface import EffectorDriver, HardwareDriver, SensorDriver
from evolver.history.interface import History
from evolver.history.standard import HistoryServer
from evolver.logutils import EVENT, CaptureHandler
from evolver.serial import EvolverSerialUART
from evolver.settings import settings

DEFAULT_SERIAL = EvolverSerialUART
DEFAULT_HISTORY = HistoryServer


class Evolver(BaseInterface):
    class Config(BaseInterface.Config):
        name: str = "Evolver"
        experiment: str = "unspecified"
        vials: list = list(range(settings.DEFAULT_NUMBER_OF_VIALS_PER_BOX))
        hardware: dict[str, ConfigDescriptor | HardwareDriver] = {}
        controllers: list[ConfigDescriptor | Controller] = []
        serial: ConfigDescriptor | Connection = ConfigDescriptor.model_validate(DEFAULT_SERIAL)
        history: ConfigDescriptor | History = ConfigDescriptor.model_validate(DEFAULT_HISTORY)
        enable_control: bool = True
        interval: int = settings.DEFAULT_LOOP_INTERVAL
        raise_loop_exceptions: bool = False
        abort_on_control_errors: bool = False
        abort_on_commit_errors: bool = False
        skip_control_on_read_failure: bool = True
        log_level: int = EVENT
        log_logger: str = "root"  # though we might want to prefix things in this package with package name?

    def __init__(self, *args, **kwargs):
        self.last_read = defaultdict(lambda: int(-1))
        super().__init__(*args, evolver=self, **kwargs)
        self._setup_log_capture()

    def _setup_log_capture(self):
        self._log_capture_handler = CaptureHandler(self.history)
        self._log_capture_handler.setLevel(self.log_level)
        logging.getLogger(self.log_logger).addHandler(self._log_capture_handler)

    def __del__(self):
        logging.getLogger(self.log_logger).removeHandler(self._log_capture_handler)

    def get_hardware(self, name):
        return self.hardware[name]

    @property
    def sensors(self):
        return {k: v for k, v in self.hardware.items() if isinstance(v, SensorDriver)}

    @property
    def effectors(self):
        return {k: v for k, v in self.hardware.items() if isinstance(v, EffectorDriver)}

    @property
    def calibration_status(self):
        """Return the calibration Status for each device's calibrator, or None if hardware has no calibrator. This is explicit and returns all available
        hardware even those without calibrators.
        """
        return {
            name: device.calibrator.status if getattr(device, "calibrator", None) else None
            for name, device in self.hardware.items()
        }

    @property
    def state(self):
        return {name: device.get() for name, device in self.sensors.items()}

    @property
    def schema(self):
        hardware_schemas = []
        for n, hw in self.hardware.items():
            s = {"name": n, "kind": str(type(hw)), "config": hw.Config.model_json_schema()}
            if isinstance(hw, SensorDriver):
                s["output"] = hw.Output.model_json_schema()
            if isinstance(hw, EffectorDriver):
                s["input"] = hw.Input.model_json_schema()
            hardware_schemas.append(s)
        return {
            "hardware": hardware_schemas,
            "controllers": [{"kind": str(type(a)), "config": a.Config.model_json_schema()} for a in self.controllers],
        }

    def _loop_exception_wrapper(self, callable, message="unknown") -> bool:
        try:
            callable()
            return None
        except Exception as exc:
            self.logger.exception(f"Error in loop: {message}")
            if self.raise_loop_exceptions:
                raise
            return exc

    def read_state(self):
        read_errors = []
        for name, device in self.sensors.items():
            read_errors.append(self._loop_exception_wrapper(device.read, f"reading device {name}"))
            self.last_read[name] = time.time()
            if data := device.get():
                self.history.put(name, "sensor", data)  # TODO: store as vials separately
        return read_errors

    def evaluate_controllers(self):
        return [self._loop_exception_wrapper(c.run, f"updating controller {c}") for c in self.controllers]

    def commit_proposals(self):
        return [
            self._loop_exception_wrapper(d.commit, f"committing proposals for {d}") for d in self.effectors.values()
        ]

    def loop_once(self):
        self.logger.info("running control loop iteration")
        read_errors = self.read_state()
        if any(read_errors) and self.skip_control_on_read_failure:
            self.logger.warning("Skipping control loop due to read error")
            return
        if self.enable_control:
            control_errors = self.evaluate_controllers()
            if any(control_errors) and self.abort_on_control_errors:
                self.abort()
                raise RuntimeError("Aborted due to control error(s) - see logs for all errors") from control_errors[0]
            commit_errors = self.commit_proposals()
            if any(commit_errors) and self.abort_on_commit_errors:
                self.abort()
                raise RuntimeError("Aborted due to commit error(s) - see logs for all errors") from commit_errors[0]

    def abort(self):
        self.enable_control = False
        for device in self.effectors.values():
            device.off()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.config_model.save(settings.SNAPSHOT)

        # TODO: Add code to stop all running hardware, which could implemented by context managing the hardware.
        ...
