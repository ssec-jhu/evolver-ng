from abc import abstractmethod

from evolver.base import BaseConfig, BaseInterface
from evolver.settings import settings


class Calibrator(BaseInterface):
    """ Base Interface class for all calibration implementations.

        A modular layer for encapsulating both the calibration conversion method (``convert``) and the calibration
        procedure itself.
    """

    class Config(BaseConfig):
        dir: str = settings.ROOT_CALIBRATOR_FILE_STORAGE_PATH  # TODO: Placeholder for #45

    @property
    @abstractmethod
    def is_calibrated(self) -> bool:
        """ Whether sufficient data has been provided to adequately exec ``self.convert()``.
            E.g., ``return None in vars(self).values()``.
        """
        ...

    @abstractmethod
    def convert(self, data):
        """ Return calibrated data.
            Note: Use Calibrator.calibrate to decorate ``evolver.hardware.interface.Device.get()``.
        """
        ...

    @abstractmethod
    def run_calibration_procedure(self, *args, **kwargs):
        """ This executes the calibration procedure. """
        # TODO: This needs more work, however, since it isn't used in the base SDK layer this can be punted. This is
        #  intended to be called from the application layer to run interactive calibration procedures. See #45.
        ...

    @staticmethod
    def calibrate(func) -> "func.__class__.OutputModel":
        """ Use to decorate, for example, ``evolver.hardware.interface.Device.get()`` to calibrate returned data. """
        def wrapper(self, *args, **kwargs):
            data = func(self, *args, **kwargs)

            # Only calibrate (convert) calibrated calibrators.
            if (((is_calibrated := getattr(self, "is_calibrated", None))
                    or ((calibrator := getattr(self, "calibrator", None))
                        and (is_calibrated := getattr(calibrator, "is_calibrated", None))))
                    and not is_calibrated()):
                return data

            # Calibrate data.
            if ((convert := getattr(self, "convert", None))
                or ((calibrator := getattr(self, "calibrator", None))
                    and (convert := getattr(calibrator, "convert", None)))):
                return convert(data)

            return data
        return wrapper
