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


def _vial_filter(vial: int, driver: VialHardwareDriver):
    try:
        if vial in driver.vial_list:
            return True
    except AttributeError:
        return False
    return False


class VialView(Vial):
    def __init__(self, vial: int, hardware: dict[str, VialHardwareDriver]):
        super().__init__(vial)
        self._hardware = hardware

    @property
    def hardware(self):
        return {k: v for k,v in self._hardware.items() if _vial_filter(self.vial, v)}

    def get(self, name: str):
        return self.hardware[name].get().get(self.vial)

    def set(self, name: str, value):
        value['vial'] = self.vial
        hw = self.hardware[name]
        in_val = hw.Input.model_validate(value)
        hw.set(in_val)


class EvolverVialView(VialView):
    def __init__(self, vial: int, evolver):
        super().__init__(vial, evolver)

    @property
    def hardware(self):
        return {k: v for k,v in self._hardware.hardware.items() if _vial_filter(self.vial, v)}
