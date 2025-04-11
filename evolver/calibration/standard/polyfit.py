from typing import Self

import numpy.polynomial.polynomial as poly
from pydantic import Field, model_validator

from evolver.base import ConfigDescriptor
from evolver.calibration.interface import Calibrator, IndependentVialBasedCalibrator, Transformer
from evolver.settings import settings


class PolyFitTransformer(Transformer):
    class Config(Transformer.Config):
        degree: int = Field(ge=0, description="Polynomial degree.")
        parameters: list[float] | None = Field(default=None, min_length=1, description="Polynomial coefficients.")

        @model_validator(mode="after")
        def check_parameters_length(self) -> Self:
            # Only validate parameters if they are provided.
            if self.parameters and (len(self.parameters) - 1 != self.degree):
                raise ValueError(f"Degree={self.degree} but {len(self.parameters)} parameters given.")
            return self

    @classmethod
    def fit(cls, x, y, deg, *args, **kwargs):
        new_parameters = poly.polyfit(x, y, deg, *args, **kwargs)
        config = cls.Config.model_validate(dict(parameters=new_parameters))
        return config

    def refit(self, x, y, *args, **kwargs):
        return super().refit(x, y, self.degree, *args, **kwargs)

    def convert_to(self, x):
        # Check if parameters exist before attempting to use them
        if self.parameters is None:
            return None
        return poly.polyval(x, self.parameters)

    def convert_from(self, y):
        # Check if parameters exist before attempting to use them
        if self.parameters is None:
            return None
        return (poly.Polynomial(self.parameters) - y).roots()


class LinearTransformer(PolyFitTransformer):
    class Config(PolyFitTransformer.Config):
        degree: int = Field(1, ge=1, le=1, description="Polynomial degree.", frozen=True)

    @classmethod
    def fit(cls, x, y, *args, **kwargs):
        return super().fit(x, y, 1, *args, **kwargs)

    def refit(self, x, y, *args, **kwargs):
        return super().refit(x, y, *args, **kwargs)

    def convert_from(self, y):
        result = super().convert_from(y)
        if result is None:
            return None
        return result[0]


class PolyFitCalibrator(Calibrator):
    def run_calibration_procedure(self, data: dict, save=settings.AUTO_SAVE_NEW_CALIBRATIONS):
        # TODO: This is just a placeholder.
        calibration_data = {}
        for transformer, (x, y) in data.items():
            calibration_data[transformer] = getattr(self, transformer).refit(x, y)
            if save:
                calibration_data[transformer].save()
        return calibration_data

    def create_calibration_procedure(*args, **kwargs):
        raise NotImplementedError


class LinearCalibrator(PolyFitCalibrator):
    class Config(PolyFitCalibrator.Config):
        input_transformer: ConfigDescriptor | None = None
        output_transformer: ConfigDescriptor | None = None


class IndependentVialBasedLinearCalibrator(IndependentVialBasedCalibrator):
    def run_calibration_procedure(self, data: dict):
        """Override to implement a calibration procedure that is vial-dependant and thus calibrates all vials either
        simultaneously or entirely as desired."""

        calibration_data = dict(input_transformer={}, output_transformer={})

        # Sequentially run calibration procedure for the input transformer for each vial.
        for vial, input_transformer in self.input_transformer.items():
            calibration_data["input_transformer"][vial] = input_transformer.run_calibration_procedure(
                data["input_transformer"][vial]
            )

        # Sequentially run calibration procedure for the output transformer for each vial.
        for vial, output_transformer in self.output_transformer.items():
            calibration_data["output_transformer"][vial] = output_transformer.run_calibration_procedure(
                data["output_transformer"][vial]
            )

    def create_calibration_procedure(*args, **kwargs):
        raise NotImplementedError
