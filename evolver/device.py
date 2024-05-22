import time
import pydantic
from typing import Annotated
from evolver.hardware.interface import SensorDriver, EffectorDriver
from evolver.serial import EvolverSerialUART
from evolver.history import HistoryServer


DEFAULT_SERIAL = EvolverSerialUART
DEFAULT_HISTORY = HistoryServer
# pydantics import string alone does not generate a schema, which breaks openapi
# docs. We wrap it to set schema explicitly.
ImportString = Annotated[
    pydantic.ImportString, pydantic.WithJsonSchema({'type': 'string', 'description': 'fully qualified class name'})
]


class ControllerDescriptor(pydantic.BaseModel):
    driver: ImportString
    config: dict = {}

    def driver_from_descriptor(self, evolver):
        conf = self.driver.Config.model_validate(self.config)
        return self.driver(evolver, conf)


class HardwareDriverDescriptor(ControllerDescriptor):
    calibrator: ControllerDescriptor = None


class EvolverConfig(pydantic.BaseModel):
    vials: list = list(range(16))
    hardware: dict[str, HardwareDriverDescriptor] = {}
    controllers: list[ControllerDescriptor] = []
    serial: ControllerDescriptor = ControllerDescriptor(driver=DEFAULT_SERIAL, config=DEFAULT_SERIAL.Config().model_dump())
    history: ControllerDescriptor = ControllerDescriptor(driver=DEFAULT_HISTORY, config=DEFAULT_HISTORY.Config().model_dump())
    enable_control: bool = True
    enable_commit: bool = True
    interval: int = 20


class Evolver:
    def __init__(self, config: EvolverConfig = EvolverConfig()):
        self.hardware = {}
        self.last_read = {}
        self.controllers = []
        self.update_config(config)

    def update_config(self, config: EvolverConfig):
        self.config = config
        for name, driver in config.hardware.items():
            self.setup_driver(name, driver)
        for name in list(self.hardware.keys()):
            if name not in config.hardware.keys():
                del(self.hardware[name])
                del(self.last_read[name])
        self.controllers = []
        for controller in config.controllers:
            self.setup_controller(controller)
        if config.serial is not None:
            self.serial = config.serial.driver_from_descriptor(self)
        else:
            self.serial = DEFAULT_SERIAL()
        if config.history is not None:
            self.history = config.history.driver_from_descriptor(self)
        else:
            self.history = DEFAULT_HISTORY()

    def setup_driver(self, name, driver_config: HardwareDriverDescriptor):
        config = driver_config.driver.Config.model_validate(driver_config.config)
        calibrator = None
        if driver_config.calibrator is not None:
            calibrator = driver_config.calibrator.driver_from_descriptor(self)
        self.hardware[name] = driver_config.driver(self, config, calibrator)
        self.last_read[name] = -1

    def setup_controller(self, controller):
        self.controllers.append(controller.driver_from_descriptor(self))

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
            'controllers': [{'kind': str(type(a)), 'config': a.Config.model_json_schema()} for a in self.controllers],
        }

    def read_state(self):
        for name, device in self.sensors.items():
            device.read()
            self.last_read[name] = time.time()
            self.history.put(name, device.get())

    def evaluate_controllers(self):
        for controller in self.controllers:
            controller.run()

    def commit_proposals(self):
        for device in self.effectors.values():
            device.commit()

    def loop_once(self):
        self.read_state()
        # for any hardware awaiting calibration, call calibration update method here
        if self.config.enable_control:
            self.evaluate_controllers()
        if self.config.enable_commit:
            self.commit_proposals()
