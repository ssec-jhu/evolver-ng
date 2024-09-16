import numpy as np

from evolver.calibration.standard.curve_fit import CurveFitTransformer


class SigmoidFitTransformer(CurveFitTransformer):
    @staticmethod
    def func_to(x, a, b, c, d):
        # Copied from https://github.com/FYNCH-BIO/evolver-electron/blob/75f01fea44983be0260f6d6697440f1de0c4dfa3/app/components/Setup.js#L265-L266
        return c - ((np.log10((b - a) / (x - a) - 1)) / d)

    @staticmethod
    def func_from(x, a, b, c, d):
        # Copied from https://github.com/FYNCH-BIO/dpu/blob/1ea8fe36a6a7cdbcf4e5a872c43abfdf53acaf35/calibration/calibrate.py#L52-L53
        return a + (b - a) / (1 + (10 ** ((c - x) * d)))
