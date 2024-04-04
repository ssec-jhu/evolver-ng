from abc import ABC, abstractmethod
from evolver.hardware.interface import VialHardwareDriver


class Vial(ABC):
    def __init__(self, vial: int):
        self.vial = vial

    @abstractmethod
    def get(driver_name: str):
        pass

    @abstractmethod
    def set(driver_name: str, value):
        pass


class VialView(Vial):
    def __init__(self, vial: int, hardware: dict[str, VialHardwareDriver]):
        super().__init__(vial)
        self.hardware: dict[str, VialHardwareDriver] = {}
        for name, driver in hardware.items():
            try:
                if vial in driver.vial_list:
                    self.hardware[name] = driver
            except AttributeError:
                pass

    def get(self, name: str):
        return self.hardware[name].get().get(self.vial)

    def set(self, name: str, value):
        hw = self.hardware[name]
        value['vial'] = self.vial
        in_val = hw.Input.model_validate(value)
        hw.set(in_val)
