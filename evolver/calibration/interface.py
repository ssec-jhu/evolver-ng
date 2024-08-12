import datetime
from abc import abstractmethod
from pathlib import Path
from typing import Any

from pydantic import Field, PastDatetime

from evolver.base import (
    BaseConfig,
    BaseInterface,
    ConfigDescriptor,
    CreatedTimestampField,
    ExpireField,
    TimeStamp,
    _BaseConfig,
)
from evolver.settings import settings


class Status(TimeStamp):
    delta: datetime.timedelta | None = Field(None, description="The time delta between now and `timestamp`.")
    ok: bool | None = Field(None, description="The associated calibration config is stale when False and ok when True.")

    def model_post_init(self, __context: Any) -> None:
        # Compute status age.
        if self.delta is None:
            self.delta = datetime.datetime.now() - self.created

        # Is status OK?
        if self.expire is None:
            self.ok = True
        elif self.ok is None:
            self.ok = self.delta <= self.expire


def root_calibrator_file_storage_path():
    """Defer this such that it can be monkeypatched during tests."""
    return settings.ROOT_CALIBRATOR_FILE_STORAGE_PATH


class Transformer(BaseInterface):
    """Base Interface class for implementing transformations.

    A modular layer for encapsulating the transformation and conversion methods between, e.g., raw and un-raw values,
    or conversion between units etc. This can also be used for such transformations as needed for transforming between
    uncalibrated and calibrated values.
    """

    class Config(BaseConfig):
        dir: Path = Field(
            default_factory=root_calibrator_file_storage_path,
            description="Directory for saving new configuration files to.",
        )
        created: PastDatetime | None = CreatedTimestampField()
        expire: datetime.timedelta | None = ExpireField(default=settings.DEFAULT_CALIBRATION_EXPIRE)

        def save(self, file_path: Path = None, encoding: str | None = None):
            if file_path is None:
                file_path = Path(f"{self.name}_{self.created.strftime(settings.DATETIME_PATH_FORMAT)}").with_suffix(
                    ".yml"
                )
            return super().save(file_path=self.dir / file_path, encoding=encoding)

    @abstractmethod
    def convert_to(self, *args, **kwargs):
        """Implement and return some transformation upon the input.
        This is the inverse transformation of ``convert_from`
        """
        ...

    @abstractmethod
    def convert_from(self, *args, **kwargs):
        """Implement and return some transformation upon the input.
        This is the inverse transformation of ``convert_to`
        """
        ...

    @property
    def status(self) -> Status:
        """Override to return an instance of Status indicating whether the associated transformation config parameters
        are OK to use or should be considered stale and recalibrated.
        """
        return Status(created=self.created, expire=self.expire)

    @classmethod
    def fit(cls, *args, **kwargs) -> Config:
        """Override to implement a fitting function responsible for returning a ``Config`` instance that can then be
        used for ``convert_to`` and ``convert_from``.
        This can be utilized by ``Calibrator.run_calibration_procedure``, however, because the fit produces config
        parameters directly related to the transformation, such definitions must belong to the transformer and not
        the calibrator class.
        """
        # Note: This is intentionally not an abstractmethod.
        raise NotImplementedError

    def refit(self, *args, **kwargs):
        new_config = self.fit(*args, **kwargs)
        for k, v in vars(new_config).items():
            setattr(self, k, v)
        return new_config


class Calibrator(BaseInterface):
    """Base Interface class for all calibration implementations.

    A modular layer for encapsulating the calibration procedure and data transformations.
    """

    class Config(Transformer.Config):
        input_transformer: ConfigDescriptor | Transformer | None = None
        output_transformer: ConfigDescriptor | Transformer | None = None
        measured_data: dict | None = Field(
            None,
            description="The data measured by a calibration procedure run. This can be specified instead of specifying "
            "some transformer config params, e.g., polynomial coefficients. This data will be fitted upon "
            "first use.",
        )

    class Status(_BaseConfig):
        input_transformer: Status | None = None
        output_transformer: Status | None = None
        ok: bool | None = None

        def model_post_init(self, __context: Any) -> None:
            if self.ok is None:
                # The following logic accounts for when transformers are None.
                if self.input_transformer and self.output_transformer:
                    self.ok = self.input_transformer.ok and self.output_transformer.ok
                elif self.input_transformer:
                    self.ok = self.input_transformer.ok
                elif self.output_transformer:
                    self.ok = self.output_transformer.ok

    @property
    def status(self) -> Status:
        return self.Status(
            input_transformer=self.input_transformer.status if self.input_transformer else None,
            output_transformer=self.output_transformer.status if self.output_transformer else None,
        )

    @abstractmethod
    def run_calibration_procedure(self, *args, **kwargs):
        """This executes the calibration procedure."""
        # TODO: This needs more work, however, since it isn't used in the base SDK layer this can be punted. This is
        #  intended to be called from the application layer to run interactive calibration procedures. See #45.
        # TODO: Consider transactional state if this procedure is interrupted mid way. E.g., for ``is_calibrated``.
        ...
