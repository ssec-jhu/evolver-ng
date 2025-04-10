import logging
import time
from collections import defaultdict
from math import prod

from pydantic import Field, ValidationInfo, field_serializer, field_validator

from evolver.base import BaseInterface, ConfigDescriptor
from evolver.connection.interface import Connection
from evolver.controller.interface import Controller
from evolver.hardware.interface import EffectorDriver, HardwareDriver, SensorDriver
from evolver.history.interface import History
from evolver.history.standard import HistoryServer
from evolver.logutils import EVENT, LogHistoryCaptureHandler
from evolver.serial import EvolverSerialUART
from evolver.settings import settings

DEFAULT_SERIAL = EvolverSerialUART
DEFAULT_HISTORY = HistoryServer


class Experiment(BaseInterface.Config):
    enabled: bool = True
    controllers: list[ConfigDescriptor | Controller] = []

    # this seemed to have been required for the tests of config symmetry.
    # Without it there is pydantic error about unkown type (the underlying
    # Controller class) - so seemed to be kind of bypassing the evolver
    # BaseModel hookups?
    @field_serializer("controllers")
    def serialize_controllers(self, data):
        return [ConfigDescriptor.model_validate(c) for c in data]

    @field_validator("controllers", mode="before")
    @classmethod
    def validate_controllers(cls, v):
        return [] if v is None else v


class Evolver(BaseInterface):
    class Config(BaseInterface.Config):
        name: str = "Evolver"
        namespace: str = "unspecified"
        vial_layout: list[int] = Field(
            default=settings.DEFAULT_VIAL_LAYOUT,
            description="The layout of the vials in 2 or 3 dimensions. Always left-to-right bottom-top-top order.",
            min_length=2,
            max_length=3,
        )
        vials: list = list(range(settings.DEFAULT_NUMBER_OF_VIALS_PER_BOX))
        hardware: dict[str, ConfigDescriptor | HardwareDriver] = Field(default={}, 
                description="Hardware drivers mapped by name. Preserves ConfigDescriptor types during serialization.")
        experiments: dict[str, Experiment] = {}
        serial: ConfigDescriptor | Connection = ConfigDescriptor.model_validate(DEFAULT_SERIAL)
        history: ConfigDescriptor | History = ConfigDescriptor.model_validate(DEFAULT_HISTORY)
        enable_control: bool = True
        interval: int = settings.DEFAULT_LOOP_INTERVAL
        raise_loop_exceptions: bool = False
        abort_on_control_errors: bool = False
        abort_on_commit_errors: bool = False
        skip_control_on_read_failure: bool = True
        log_level: int = EVENT

        @field_validator("hardware", "experiments", mode="before")
        @classmethod
        def validate_dicts(cls, v):
            return {} if v is None else v
            
        @field_serializer("hardware")
        def serialize_hardware(self, hardware_dict):
            """Ensures hardware items are correctly serialized.
            
            When union types (ConfigDescriptor | HardwareDriver) are used,
            Pydantic's smart union mode doesn't always preserve ConfigDescriptor
            serialization, especially with nested calibrators. This explicitly
            converts hardware drivers to ConfigDescriptor objects during serialization.
            """
            return {
                k: (v if isinstance(v, ConfigDescriptor) else ConfigDescriptor.model_validate(v))
                for k, v in hardware_dict.items()
            }

        @field_validator("vials", mode="after")
        @classmethod
        def validate_vials(cls, value: list[int], info: ValidationInfo):
            total_slots = prod(info.data["vial_layout"])
            if len(value) > total_slots or max(value) >= total_slots:
                raise ValueError(f"Vials configured exceed total available slots from layout {total_slots}")
            return value

    def __init__(self, *args, **kwargs):
        self.last_read = defaultdict(lambda: int(-1))
        super().__init__(*args, evolver=self, **kwargs)
        # We have to turn experiment controllers passed in as configdescriptors
        # to objects while passing in self so controllers can consume hardware
        # and read from history, etc.
        for experiment in self.experiments.values():
            for i in range(len(experiment.controllers)):
                elem = experiment.controllers[i]
                if isinstance(elem, ConfigDescriptor):
                    experiment.controllers[i] = elem.create(non_config_kwargs={"evolver": self})
        self._setup_log_capture()

    def _setup_log_capture(self):
        self._log_capture_handler = LogHistoryCaptureHandler(self.history)
        self._log_capture_handler.setLevel(self.log_level)
        logger = logging.getLogger(settings.DEFAULT_LOGGER)
        logger.addHandler(self._log_capture_handler)
        logger.setLevel(self.log_level)

    def __del__(self):
        if handler := getattr(self, "_log_capture_handler", None):
            logging.getLogger(settings.DEFAULT_LOGGER).removeHandler(handler)

    def get_hardware(self, name):
        return self.hardware[name]

    @property
    def sensors(self):
        return {k: v for k, v in self.hardware.items() if isinstance(v, SensorDriver)}

    @property
    def effectors(self):
        return {k: v for k, v in self.hardware.items() if isinstance(v, EffectorDriver)}

    @property
    def enabled_controllers(self):
        return [c for exp in self.experiments.values() for c in exp.controllers if exp.enabled]

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
                if isinstance(data, dict):
                    for vial, output in data.items():
                        self.history.put(name, "sensor", output, vial=vial)
                else:
                    self.history.put(name, "sensor", data, vial=getattr(data, "vial", None))
        return read_errors

    def evaluate_controllers(self):
        return [self._loop_exception_wrapper(c.run, f"updating controller {c}") for c in self.enabled_controllers]

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
        self.logger.log(EVENT, "Abort start")
        self.enable_control = False
        for device in self.effectors.values():
            device.off()
        self.logger.log(EVENT, "Abort complete - device now inactive")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.config_model.save(settings.SNAPSHOT)

        # TODO: Add code to stop all running hardware, which could implemented by context managing the hardware.
        ...
