import datetime
from abc import abstractmethod
from enum import auto, StrEnum
from pathlib import Path

from pydantic import Field

from evolver.base import BaseConfig, BaseInterface
from evolver.settings import settings


class Kind(StrEnum):
    FROM_RAW = auto()
    TO_RAW = auto()


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
    def convert_from_raw(self, data):
        """Return calibrated data from raw data. This is the inverse function of ``convert_to_raw``.
        Note: Use Calibrator.calibrate_output to decorate ``evolver.hardware.interface.SensorDriver.read()``.
        """
        ...

    @abstractmethod
    def convert_to_raw(self, data):
        """Return raw data from calibrated data. This is the inverse function of ``convert_from_raw``.
        Note: Use Calibrator.calibrate_input to decorate ``evolver.hardware.interface.SensorDriver.set()``.
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
    def calibrate(func, kind: Kind = Kind.FROM_RAW):
        """Use to decorate, e.g., ``evolver.hardware.interface.SensorDriver.read()`` to calibrate returned data."""

        kind = Kind(kind)

        def wrapper(self, *args, **kwargs):
            data = func(self, *args, **kwargs)

            if calibrator := getattr(self, "calibrator", None):
                # if isinstance(data, dict):
                #     for k, v in data.items():
                #         data[k].value = _convert(v.raw)
                # else:
                #     data.value = _convert(data.raw)

                if kind is Kind.FROM_RAW:
                    return calibrator.convert_from_raw(data)
                elif kind is Kind.TO_RAW:
                    return calibrator.convert_to_raw(data)
            return data

        return wrapper

    @classmethod
    def calibrate_output(cls, func):
        return cls.calibrate(func, kind=Kind.FROM_RAW)

    @classmethod
    def calibrate_input(cls, func):
        return cls.calibrate(func, kind=Kind.TO_RAW)
