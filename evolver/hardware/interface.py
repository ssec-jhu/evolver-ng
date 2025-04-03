from abc import abstractmethod
from typing import Any

from pydantic import Field

from evolver.base import BaseConfig, BaseInterface, ConfigDescriptor
from evolver.calibration.interface import Calibrator
from evolver.settings import settings


class VialConfigBaseModel(BaseConfig):
    vials: list[int] | None = list(range(settings.DEFAULT_NUMBER_OF_VIALS_PER_BOX))


class VialBaseModel(BaseConfig):
    vial: int


class HardwareDriver(BaseInterface):
    class Config(BaseInterface.Config):
        calibrator: ConfigDescriptor | Calibrator | None = Field(
            None, description="The calibrator used to both calibrate and transform Input and/or Output data."
        )

    def __init__(self, *args, evolver=None, **kwargs):
        self.evolver = evolver
        super().__init__(*args, **kwargs)

    def _transform(self, transformer: str, func: str, x: Any, vial: int = None, fallback=None):
        """Helper func to reduce boilerplate when transforming input and output data."""

        if self.calibrator and (_transformer := getattr(self.calibrator, transformer, None)):
            try:
                if isinstance(_transformer, dict):
                    y = getattr(_transformer[vial], func)(x)
                else:
                    y = getattr(_transformer, func)(x)
            except Exception as exc:
                self.logger.error(f"Error transforming values for {self.name} (vial {vial}): {exc}")
                y = fallback
        else:
            y = fallback

        return y


class VialHardwareDriver(HardwareDriver):
    class Config(VialConfigBaseModel, HardwareDriver.Config): ...


class SensorDriver(VialHardwareDriver):
    class Config(VialHardwareDriver.Config): ...

    class Output(VialBaseModel): ...

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.outputs: dict[int, self.Output] = {}

    def get(self) -> dict[int, Output]:
        return self.outputs

    @abstractmethod
    def read(self):
        """Communicate with connection to retrieve data. This must return ``self.outputs``.
        The implementation is responsible for calling methods of ``self.output_transformer`` as deemed necessary.
        """
        pass


class EffectorDriver(VialHardwareDriver):
    class Config(VialHardwareDriver.Config):
        pass

    class Input(VialBaseModel): ...

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.proposal: dict[int, self.Input] = {}
        self.committed: dict[int, self.Input] = {}

    def _get_input_from_args(self, *args, **kwargs):
        if kwargs and args:
            raise ValueError("Pass either an input model instance or input fields to set")
        if args:
            input = args[0]
        elif kwargs:
            input = kwargs
        else:
            raise ValueError("No input provided")
        return self.Input.model_validate(input)

    def set(self, *args, **kwargs):
        """Set a value proposal for the hardware.

        The value should either be an instance of the hardware Input model, or
        fields that will be set on said model. This method proposes individual
        values (e.g. for a single vial), which will be committed in bulk when
        the commit method is called (done typically in the experiment loop by
        the Evolver manager).

        In most cases this method need not be overridden, the logic of
        performing calibration transform, preparing data packets and
        communicating with the underlying hardware is handled in the commit
        method.
        """
        validated_input = self._get_input_from_args(*args, **kwargs)
        self.proposal[validated_input.vial] = validated_input

    @abstractmethod
    def commit(self):
        """Commit all pending proposals to the underlying hardware device.

        This method handles the logic of performing calibration transform,
        preparing data packets and communicating with the underlying hardware.
        It should be implemented by the hardware driver to perform the necessary
        actions to commit the proposals to the hardware.
        """
        pass

    @abstractmethod
    def off(self):
        """Immediately turn device into off state.

        Used by framework in aborting an experiment. Implementations should
        define off condition and implement in such a way that a commit call is
        not necessary (i.e. the device turns off upon calling this method).
        """
        pass
