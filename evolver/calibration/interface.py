import datetime
from abc import ABC, abstractmethod
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
from evolver.calibration.procedure import (
    CalibrationProcedure,
)
from evolver.calibration.actions import (
    DisplayInstructionAction,
    VialTempCalculateFitAction,
    VialTempRawVoltageAction,
    VialTempReferenceValueAction,
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

    def __init__(self, *args, evolver=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.evolver = evolver
        self.calibration_procedure = None

    @property
    def status(self) -> Status:
        return self.Status(
            input_transformer=self.input_transformer.status if self.input_transformer else None,
            output_transformer=self.output_transformer.status if self.output_transformer else None,
        )

    @abstractmethod
    def initialize_calibration_procedure(self, *args, **kwargs):
        """This initializes the calibration procedure. Subclasses should implement this method to initialize the calibration"""
        ...

    def dispatch(self, action):
        # Delegate to the calibration procedure
        if self.calibration_procedure is None:
            raise ValueError("Calibration procedure is not initialized.")
        self.state = self.calibration_procedure.dispatch(action)
        return self.state


class IndependentVialBasedCalibrator(Calibrator, ABC):
    class Config(Calibrator.Config):
        """Specify transformers for each vial independently. Whilst they may all use the same transformer class, each
        vial will mostly likely have different transformer config parameters and thus require their own transformer
        instance.
        """

        input_transformer: dict[int, ConfigDescriptor | Transformer | None] | None = None
        output_transformer: dict[int, ConfigDescriptor | Transformer | None] | None = None

    def initialize_calibration_procedure(self, *args, **kwargs): ...


# Example calibrator implementation to match existing temperature calibration flow.
class TemperatureCalibrator(Calibrator):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.state = {"selected_vials": []}

    def initialize_calibration_procedure(self, selected_vials: list[int], *args, **kwargs):
        # TODO: integrate self.state with self.CalibrationData, see Arik for context.
        self.state["selected_vials"] = selected_vials

        if not self.evolver:
            raise ValueError("Evolver must be initialized")
        if not self.evolver.hardware:
            raise ValueError("Evolver.hardware must be initialized")

        calibration_procedure = CalibrationProcedure("Temperature Calibration")
        calibration_procedure.add_action(
            DisplayInstructionAction(description="Fill each vial with 15ml water", name="Fill_Vials_With_Water")
        )
        for vial in self.state["selected_vials"]:
            calibration_procedure.add_action(
                VialTempReferenceValueAction(
                    # TODO: confirm this is the best way to get the hardware this calibrator is associated with.
                    # Risk is you cross wires and get the wrong hardware.
                    hardware=self.evolver.get_hardware(name="temp"),
                    vial_idx=vial,
                    description=f"Use a thermometer to measure the real temperature in the vial {vial}",
                    name=f"Vial_{vial}_Temp_Reference_Value_Action",
                )
            )
            calibration_procedure.add_action(
                VialTempRawVoltageAction(
                    hardware=self.evolver.get_hardware(name="temp"),
                    vial_idx=vial,
                    description=f"The hardware will now read the raw voltage from the temperature sensor, vial {vial}",
                    name=f"Vial_{vial}_Temp_Raw_Voltage_Action",
                )
            )

        # Add a final step to calculate the fit.
        for vial in self.state["selected_vials"]:
            calibration_procedure.add_action(
                VialTempCalculateFitAction(
                    hardware=self.evolver.get_hardware(name="temp"),
                    vial_idx=vial,
                    description="Use the real and raw values that have been collected to calculate the fit for the temperature sensor",
                    name=f"Vial_{vial}_Temp_Calculate_Fit_Action",
                )
            )
        self.calibration_procedure = calibration_procedure
