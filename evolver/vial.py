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


def _filter_hardwares_by_vial(vial: int, hw: dict[str, VialHardwareDriver]):
    return {k: v for k,v in hw.items() if _vial_filter(vial, v)}


class VialView(Vial):
    def __init__(self, vial: int, hardware: dict[str, VialHardwareDriver]):
        super().__init__(vial)
        self._hardware = hardware

    @property
    def hardware(self):
        return _filter_hardwares_by_vial(self.vial, self._hardware)

    def get(self, name: str):
        return self.hardware[name].get().get(self.vial)

    def set(self, name: str, value):
        value['vial'] = self.vial
        hw = self.hardware[name]
        hw.set(hw.Input.model_validate(value))


class EvolverVialView(VialView):
    def __init__(self, vial: int, evolver):
        super().__init__(vial, evolver)

    @property
    def hardware(self):
        return _filter_hardwares_by_vial(self.vial, self._hardware.hardware)
