import datetime
from abc import abstractmethod
from pathlib import Path

from pydantic import Field

from evolver.base import BaseConfig, BaseInterface
from evolver.settings import settings


class Calibrator(BaseInterface):
    """Base Interface class for all calibration implementations.

    A modular layer for encapsulating both the calibration conversion method (``convert``) and the calibration
    procedure itself.
    """

    class Config(BaseConfig):
        dir: Path = Field(
            settings.ROOT_CALIBRATOR_FILE_STORAGE_PATH, description="Directory for saving new calibration files."
        )

        def save(self, file_path: Path = None, encoding: str | None = None):
            if file_path is None:
                file_path = Path(
                    f"{self.name}_{datetime.datetime.now().strftime(settings.DATETIME_PATH_FORMAT)}"
                ).with_suffix(".yml")
            return super().save(file_path=self.dir / file_path, encoding=encoding)

    @property
    @abstractmethod
    def is_calibrated(self) -> bool:
        """Whether sufficient data has been provided to adequately exec ``self.convert()``."""
        ...

    @abstractmethod
    def convert(self, data):
        """Return calibrated data.
        Note: Use Calibrator.calibrate to decorate ``evolver.hardware.interface.SensorDriver.get()``.
        """
        ...

    @abstractmethod
    def run_calibration_procedure(self, *args, **kwargs):
        """This executes the calibration procedure."""
        # TODO: This needs more work, however, since it isn't used in the base SDK layer this can be punted. This is
        #  intended to be called from the application layer to run interactive calibration procedures. See #45.
        # TODO: Consider transactional state if this procedure is interrupted mid way. E.g., for ``is_calibrated``.
        ...

    @staticmethod
    def calibrate(func):
        """Use to decorate, e.g., ``evolver.hardware.interface.SensorDriver.get()`` to calibrate returned data."""

        def wrapper(self, *args, **kwargs):
            data = func(self, *args, **kwargs)

            # Only calibrate (convert) calibrated calibrators.
            if (calibrator := getattr(self, "calibrator", None)) and calibrator.is_calibrated:
                return calibrator.convert(data)

            return data

        return wrapper
