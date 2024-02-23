import time
from pydantic import BaseModel
from evolver.util import load_class_fqcn
from evolver.hardware import SensorDriver, EffectorDriver


class AdapterDescriptor(BaseModel):
    driver: str
    config: dict = {}


class HardwareDriverDescriptor(AdapterDescriptor):
    calibrator: AdapterDescriptor = None


class EvolverConfig(BaseModel):
    vials: list = list(range(16))
    hardware: dict[str, HardwareDriverDescriptor] = {}
    adapters: list[AdapterDescriptor] = []
    serial: AdapterDescriptor = None
    enable_react: bool = True
    enable_commit: bool = True
    interval: int = 20


class Evolver:
    hardware = {}
    adapters = []
    last_read = {}

    def __init__(self, config: EvolverConfig = EvolverConfig()):
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
        self.setup_serial(config.serial)

    def setup_driver(self, name, driver_config: HardwareDriverDescriptor):
        driver_class = load_class_fqcn(driver_config.driver)
        config = driver_class.Config.model_validate(driver_config.config)
        calibrator = None
        if driver_config.calibrator is not None:
            calibrator_class = load_class_fqcn(driver_config.calibrator.driver)
            calibrator_config = calibrator_class.Config.model_validate(driver_config.calibrator.config)
            calibrator = calibrator_class(calibrator_config)
        self.hardware[name] = driver_class(self, config, calibrator)

    def setup_adapter(self, adapter):
        cls = load_class_fqcn(adapter.driver)
        conf = cls.Config.model_validate(adapter.config)
        self.adapters.append(cls(self, conf))

    def setup_serial(self, serial):
        pass

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

    def read_state(self):
        for name, device in self.sensors.items():
            device.read()
            self.last_read[name] = time.time()

    def get_state(self):
        return {name: device.get() for name,device in self.sensors.items()}

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
