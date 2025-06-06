import datetime
from abc import ABC, abstractmethod
from copy import copy
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List

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

if TYPE_CHECKING:
    pass


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

        def save(
            self,
            file_path: Path = None,
            encoding: str | None = None,
        ):
            if file_path is None:
                file_path = Path(f"{self.name}_{self.created.strftime(settings.DATETIME_PATH_FORMAT)}").with_suffix(
                    ".yml"
                )
            return super().save(file_path=self.dir / file_path, encoding=encoding)

        @classmethod
        def load(cls, file_path: str | Path, encoding: str | None = None):
            """Loads a configuration from a file path.

            Handles both absolute paths and relative paths. For relative paths,
            it resolves them against the appropriate storage directory.
            """
            # Check if file_path is an absolute path
            if Path(file_path).is_absolute():
                resolved_file_path = file_path
            else:
                # Use the root calibrator file storage path as default
                storage_dir = root_calibrator_file_storage_path()
                resolved_file_path = storage_dir / file_path

            return super().load(file_path=resolved_file_path, encoding=encoding)

    @abstractmethod
    def convert_to(self, *args, **kwargs):
        """Implement and return some transformation upon the input.

        The advice for conversion methods used in hardware is as follows:

            - Hardware should use the convert_to method on an output transformer to
              convert from raw values (e.g. voltages) to real-world values (e.g.
              temperature) for sensors.
            - Hardware should use the convert_from method on an input transformer to
              convert from real-world values (e.g. temperature) to raw values (e.g.
              voltages) for effectors.

        The inverse transformation of this is ``convert_from`` and should be
        used per the advice above.
        """
        ...

    @abstractmethod
    def convert_from(self, *args, **kwargs):
        """Implement and return some transformation upon the input.
        This is the inverse transformation of ``convert_to`. See documentation for
        ``convert_to`` for more information.
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


class CalibrationStateModel(Transformer.Config):
    """
    Model to represent the state of a calibration procedure. All procedures record their completed actions, and history of actions in this model.
    The data collected by the calibration procedure (i.e. the data the actions have gathered, that's used as input to the Hardware.input/outputTransformer methods) is also stored here.

    Attributes:
        started (bool): A flag to indicate if the calibration procedure has been initialized, used by the front end to determine procedure controls to display.
        completed_actions (List[str]): A list of actions that have been completed during the calibration procedure.
        history: A list of previous states of the calibration procedure. Used to undo actions.
        measured (Dict[Any, Any]): A dictionary of data collected by the calibration procedure.
            This data is used by the Transformer class to fit a model to the data.
            For example, a temperature calibrator might collect raw and reference temperature data for each vial.
    """

    class Config:
        extra = "allow"

    completed_actions: List[str] = Field(default_factory=list)
    history: List["CalibrationStateModel"] = Field(default_factory=list)
    started: bool = False
    measured: Dict[Any, Any] = {}
    fitted_calibrator: ConfigDescriptor | None = None


class Calibrator(BaseInterface):
    """Base Interface class for all calibration implementations.

    A modular layer for encapsulating the calibration procedure and data transformations.
    """

    class Config(Transformer.Config):
        input_transformer: Transformer | None = None
        output_transformer: Transformer | None = None
        no_refit: bool = Field(False, description="If True, use only cached fitted transfomers from calibration_file")
        calibration_file: str | None = Field(
            None,
            description="Completed calibration file (created when a procedure_file is complete, using the 'apply' button). Contents of this file is used as input values for transformation",
        )
        procedure_file: str | None = Field(
            None, description="Working calibration file for currently active (or next) procedure"
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

    def __init__(self, *args, calibration_file=None, procedure_file=None, **kwargs):
        super().__init__(*args, calibration_file=calibration_file, procedure_file=procedure_file, **kwargs)
        if procedure_file is not None and procedure_file == calibration_file:
            raise ValueError("to prevent corruption procedure_file must not be set to the same as calibration_file")
        if calibration_file:
            self.calibration_file = calibration_file
            self.load_calibration_file(calibration_file)
        else:
            self.calibration_data = CalibrationStateModel()

    @property
    def status(self) -> Status:
        return self.Status(
            input_transformer=self.input_transformer.status if self.input_transformer else None,
            output_transformer=self.output_transformer.status if self.output_transformer else None,
        )

    def load_calibration_file(self, calibration_file: str | None = None):
        if calibration_file is not None:
            self.load_calibration(CalibrationStateModel.load(calibration_file))
        else:
            raise ValueError("no calibration file provided")

    def load_calibration(self, calibration_data: CalibrationStateModel):
        self.calibration_data = calibration_data
        # If calibration data is provided, there are two choices that make
        # sense: either we want to refit from measured data using the configured
        # transformer classes, or we use the cached fitted ones. No measurements
        # means we must use the cached fitted ones.
        if self.no_refit or not self.calibration_data.measured:
            if self.calibration_data.fitted_calibrator is None:
                raise ValueError("Calibration data must have a fitted calibrator in case of no_refit or no measured")
            fitted_calibrator = self.calibration_data.fitted_calibrator.create()
            self.input_transformer = fitted_calibrator.input_transformer
            self.output_transformer = fitted_calibrator.output_transformer
        else:
            self.init_transformers(calibration_data)

    def init_transformers(self, calibration_data: CalibrationStateModel):
        """Initialize transformers from calibration procedure measured data.

        The shape of measurement data specific to the calibrator, so this method
        must likewise be overridden by a subclass to refit transformers as
        needed based on measured data. It should set self.input_transformer and
        self.output_transformer.
        """
        ...

    @abstractmethod
    def create_calibration_procedure(self, selected_hardware, resume, *args, **kwargs):
        """This creates the calibration procedure, which is composed of a sequence of actions."""
        pass

    def dispatch(self, action):
        """Delegate to the calibration procedure"""
        if self.calibration_procedure is None:
            raise ValueError("Calibration procedure is not initialized.")
        return self.calibration_procedure.dispatch(action)


class IndependentVialBasedCalibrator(Calibrator, ABC):
    class Config(Calibrator.Config):
        """Specify transformers for each vial independently. Whilst they may all use the same transformer class, each
        vial will mostly likely have different transformer config parameters and thus require their own transformer
        instance.
        """

        vials: list = Field(
            list(range(settings.DEFAULT_NUMBER_OF_VIALS_PER_BOX)),
            description="The vials that this calibrator is for.",
        )
        default_input_transformer: Transformer | None = None
        default_output_transformer: Transformer | None = None
        input_transformer: dict[int, Transformer | None] | None = None
        output_transformer: dict[int, Transformer | None] | None = None

    def get_input_transformer(self, vial):
        """Get the input transformer for a given vial."""
        self.input_transformer = {} if self.input_transformer is None else self.input_transformer
        return self.input_transformer.setdefault(int(vial), copy(self.default_input_transformer))

    def get_output_transformer(self, vial):
        """Get the output transformer for a given vial."""
        self.output_transformer = {} if self.output_transformer is None else self.output_transformer
        return self.output_transformer.setdefault(int(vial), copy(self.default_output_transformer))
