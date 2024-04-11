import time
import pydantic
from evolver.util import load_class_fqcn
from evolver.hardware.interface import SensorDriver, EffectorDriver
from evolver.serial import EvolverSerialUART
from evolver.history import HistoryServer


DEFAULT_SERIAL = EvolverSerialUART
DEFAULT_HISTORY = HistoryServer


# TODO: Move this to a more generic location.
class ConfigDescriptor(pydantic.BaseModel):
    classinfo: str
    config: dict = {}

    def create(self):
        cls = load_class_fqcn(self.classinfo)
        return cls(**cls.Config.model_validate(self.config).model_dump())


class AdapterDescriptor(pydantic.BaseModel):
    driver: str
    config: dict = {}

    def driver_from_descriptor(self, evolver):
        cls = load_class_fqcn(self.driver)
        conf = cls.Config.model_validate(self.config)
        return cls(evolver, conf)


class HardwareDriverDescriptor(AdapterDescriptor):
    calibrator: AdapterDescriptor = None


class EvolverConfig(pydantic.BaseModel):
    vials: list = list(range(16))
    hardware: dict[str, HardwareDriverDescriptor] = {}
    adapters: list[AdapterDescriptor] = []
    serial: AdapterDescriptor = None
    history: AdapterDescriptor = None
    enable_react: bool = True
    enable_commit: bool = True
    interval: int = 20


class Evolver:
    def __init__(self, config: EvolverConfig = EvolverConfig()):
        self.hardware = {}
        self.last_read = {}
        self.adapters = []
        self.update_config(config)

    def update_config(self, config: EvolverConfig):
        self.config = config
        for name, driver in config.hardware.items():
            self.setup_driver(name, driver)
        for name in list(self.hardware.keys()):
            if name not in config.hardware.keys():
                del(self.hardware[name])
                del(self.last_read[name])
        self.adapters = []
        for adapter in config.adapters:
            self.setup_adapter(adapter)
        if config.serial is not None:
            self.serial = config.serial.driver_from_descriptor(self)
        else:
            self.serial = DEFAULT_SERIAL()
        if config.history is not None:
            self.history = config.history.driver_from_descriptor(self)
        else:
            self.history = DEFAULT_HISTORY()

    def setup_driver(self, name, driver_config: HardwareDriverDescriptor):
        driver_class = load_class_fqcn(driver_config.driver)
        config = driver_class.Config.model_validate(driver_config.config)
        calibrator = None
        if driver_config.calibrator is not None:
            calibrator = driver_config.calibrator.driver_from_descriptor(self)
        self.hardware[name] = driver_class(self, config, calibrator)
        self.last_read[name] = -1

    def setup_adapter(self, adapter):
        self.adapters.append(adapter.driver_from_descriptor(self))

    def get_hardware(self, name):
        return self.hardware[name]

    @property
    def sensors(self):
        return {k: v for k,v in self.hardware.items() if isinstance(v, SensorDriver)}

    @property
    def effectors(self):
        return {k: v for k,v in self.hardware.items() if isinstance(v, EffectorDriver)}

    @property
    def calibration_status(self):
        return {name: device.calibrator.status for name,device in self.hardware.items()}

    @property
    def state(self):
        return {name: device.get() for name,device in self.sensors.items()}

    @property
    def schema(self):
        hardware_schemas = []
        for n, hw in self.hardware.items():
            s = {'name': n, 'kind': str(type(hw)),'config': hw.Config.model_json_schema()}
            if isinstance(hw, SensorDriver):
                s['output'] = hw.Output.model_json_schema()
            if isinstance(hw, EffectorDriver):
                s['input'] = hw.Input.model_json_schema()
            hardware_schemas.append(s)
        return {
            'hardware': hardware_schemas,
            'adapters': [{'kind': str(type(a)), 'config': a.Config.model_json_schema()} for a in self.adapters],
        }

    def read_state(self):
        for name, device in self.sensors.items():
            device.read()
            self.last_read[name] = time.time()
            self.history.put(name, device.get())

    def evaluate_adapters(self):
        for adapter in self.adapters:
            adapter.react()

    def commit_proposals(self):
        for device in self.effectors.values():
            device.commit()

    def loop_once(self):
        self.read_state()
        # for any hardware awaiting calibration, call calibration update method here
        if self.config.enable_react:
            self.evaluate_adapters()
        if self.config.enable_commit:
            self.commit_proposals()
