from typing import Self

import numpy.polynomial.polynomial as poly
from pydantic import Field, model_validator

from evolver.base import ConfigDescriptor
from evolver.calibration.interface import Calibrator, Transformer


class PolyFitTransformer(Transformer):
    class Config(Transformer.Config):
        degree: int = Field(ge=0, description="Polynomial degree.")
        coefficients: list[float] = Field(min_length=1, description="Polynomial coefficients.")

        @model_validator(mode="after")
        def check_coefficients_length(self) -> Self:
            if len(self.coefficients) - 1 != self.degree:
                raise ValueError(f"Degree={self.degree} but {len(self.coefficients)} coefficients given.")
            return self

    @classmethod
    def fit(cls, x, y, deg, *args, **kwargs):
        new_coefficients = poly.polyfit(x, y, deg, *args, **kwargs)
        config = cls.Config.model_validate(dict(coefficients=new_coefficients))
        return config

    def refit(self, x, y, *args, **kwargs):
        return super().refit(x, y, self.degree, *args, **kwargs)

    def convert_to(self, x):
        return poly.polyval(x, self.coefficients)

    def convert_from(self, y):
        return (poly.Polynomial(self.coefficients) - y).roots()


class LinearTransformer(PolyFitTransformer):
    class Config(PolyFitTransformer.Config):
        degree: int = Field(1, ge=1, le=1, description="Polynomial degree.", frozen=True)

    @classmethod
    def fit(cls, x, y, *args, **kwargs):
        return super().fit(x, y, 1, *args, **kwargs)

    def refit(self, x, y, *args, **kwargs):
        return super().refit(x, y, *args, **kwargs)

    def convert_from(self, y):
        return super().convert_from(y)[0]


class PolyFitCalibrator(Calibrator):
    def run_calibration_procedure(self, data: dict):
        # TODO: This is just a placeholder.
        calibration_data = {}
        for transformer, (x, y) in data.items():
            calibration_data[transformer] = getattr(self, transformer).refit(x, y)
            calibration_data[transformer].save()
        return calibration_data


class LinearCalibrator(PolyFitCalibrator):
    class Config(PolyFitCalibrator.Config):
        input_transformer: ConfigDescriptor | LinearTransformer | None = None
        output_transformer: ConfigDescriptor | LinearTransformer | None = None
