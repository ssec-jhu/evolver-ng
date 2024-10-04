from abc import ABC, abstractmethod

from pydantic import Field
from scipy.optimize import curve_fit

from evolver.calibration.interface import IndependentVialBasedCalibrator, Transformer


class CurveFitTransformer(Transformer, ABC):
    class Config(Transformer.Config):
        parameters: list[float] = Field(description="Transformer parameters")

    @classmethod
    @abstractmethod
    def func_to(cls, x, *args, **kwargs):
        """Inverse function of `func_from`. Used in `self.convert_to`."""
        ...

    @classmethod
    @abstractmethod
    def func_from(cls, y, *args, **kwargs):
        """The model func to fit to.
        Inverse function of `func_to`. Used in `self.convert_from`."""
        ...

    @classmethod
    def fit(cls, x, y, *args, **kwargs):
        """Use `scipy.optimize.curve_fit for non-linear least squares to fit a function, `cls.func_from`, to data.
        See https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.curve_fit.html
        """
        new_parameters, *_other = curve_fit(cls.func_from, x, y, *args, **kwargs)
        config = cls.Config.model_validate(dict(parameters=new_parameters))
        return config

    def convert_to(self, x):
        return self.func_to(x, *self.parameters)

    def convert_from(self, y):
        return self.func_from(y, *self.parameters)


class IndependentVialBasedCurveFitCalibrator(IndependentVialBasedCalibrator):
    def run_calibration_procedure(self, *args, **kwargs):
        raise NotImplementedError
