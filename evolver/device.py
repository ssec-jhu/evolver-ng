import time
from collections import defaultdict

from evolver.base import BaseInterface, ConfigDescriptor
from evolver.connection.interface import Connection
from evolver.controller.interface import Controller
from evolver.hardware.interface import EffectorDriver, HardwareDriver, SensorDriver
from evolver.history.interface import History
from evolver.history.standard import HistoryServer
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
        skip_control_on_read_failure: bool = True

    def __init__(self, *args, **kwargs):
        self.last_read = defaultdict(lambda: int(-1))
        super().__init__(*args, evolver=self, **kwargs)

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
            return False
        except Exception as e:
            self.logger.exception(f"Error in loop: {message}: {e}")
            if self.raise_loop_exceptions:
                raise e
            return True

    def read_state(self):
        read_error = False
        for name, device in self.sensors.items():
            err = self._loop_exception_wrapper(device.read, f"reading device {name}")
            read_error = read_error or err
            self.last_read[name] = time.time()
            self.history.put(name, device.get())
        return read_error

    def evaluate_controllers(self):
        for controller in self.controllers:
            self._loop_exception_wrapper(controller.run, f"updating controller {controller}")

    def commit_proposals(self):
        for device in self.effectors.values():
            self._loop_exception_wrapper(device.commit, f"committing proposals for {device}")

    def loop_once(self):
        read_error = self.read_state()
        if read_error and self.skip_control_on_read_failure:
            self.logger.info("Skipping control loop due to read error")
            return
        # for any hardware awaiting calibration, call calibration update method here
        if self.enable_control:
            self.evaluate_controllers()
            self.commit_proposals()

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
