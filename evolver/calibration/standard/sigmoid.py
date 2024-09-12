import numpy as np

from evolver.calibration.standard.curve_fit import CurveFitTransformer


class SigmoidFitTransformer(CurveFitTransformer):
    @staticmethod
    def func_to(x, a, b, c, d):
        return c - ((np.log10((b - a) / (x - a) - 1)) / d)

    @staticmethod
    def func_from(x, a, b, c, d):
        return a + (b - a) / (1 + (10 ** ((c - x) * d)))
