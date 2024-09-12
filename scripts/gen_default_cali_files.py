from datetime import datetime

import requests

from evolver.base import ConfigDescriptor
from evolver.calibration.standard.curve_fit import IndependentVialBasedCurveFitCalibrator
from evolver.calibration.standard.polyfit import (
    IndependentVialBasedLinearCalibrator,
    LinearTransformer,
)
from evolver.calibration.standard.sigmoid import SigmoidFitTransformer
from evolver.settings import settings
from evolver.util import fully_qualified_name


def create_calibrator_config_file(
    filename,
    url,
    timestamp,
    i,
    j,
    calibrator,
    transformer,
    reverse=False,
    input_trans=True,
    output_trans=True,
):
    data = requests.get(url).json()

    coefficients = data[i]["fits"][j]["coefficients"]

    descriptor = ConfigDescriptor(
        classinfo=calibrator,
        config={
            "output_transformer": {
                vial: ConfigDescriptor(
                    classinfo=transformer,
                    config={"coefficients": coeffs[::-1] if reverse else coeffs, "created": timestamp},
                )
                for vial, coeffs in enumerate(coefficients)
            }
            if output_trans
            else None,
            "input_transformer": {
                vial: ConfigDescriptor(
                    classinfo=transformer,
                    config={"coefficients": coeffs[::-1] if reverse else coeffs, "created": timestamp},
                )
                for vial, coeffs in enumerate(coefficients)
            }
            if input_trans
            else None,
        },
    )
    descriptor.save(filename)


if __name__ == "__main__":
    url = "https://raw.githubusercontent.com/FYNCH-BIO/evolver/694ffbd91d6392bb84f2675f95c6fa81add58f03/evolver/calibrations.json"

    # Note: there doesn't seem to be a concrete format that makes it worth parsing stuff, so we just explicitly set.
    create_calibrator_config_file(
        filename=settings.DEFAULT_TEMPERATURE_CALIBRATION_CONFIG_FILE,
        url=url,
        timestamp=datetime(year=2019, month=2, day=1),
        i=1,
        j=0,
        calibrator=fully_qualified_name(IndependentVialBasedLinearCalibrator),
        transformer=fully_qualified_name(LinearTransformer),
        reverse=True,
    )

    create_calibrator_config_file(
        filename=settings.DEFAULT_OD90_CALIBRATION_CONFIG_FILE,
        url=url,
        timestamp=datetime(year=2019, month=9, day=6),
        i=2,
        j=0,
        calibrator=fully_qualified_name(IndependentVialBasedCurveFitCalibrator),
        transformer=fully_qualified_name(SigmoidFitTransformer),
        input_trans=False,
        output_trans=True,
    )

    create_calibrator_config_file(
        filename=settings.DEFAULT_OD135_CALIBRATION_CONFIG_FILE,
        url=url,
        timestamp=datetime(year=2019, month=9, day=6),
        i=2,
        j=1,
        calibrator=fully_qualified_name(IndependentVialBasedCurveFitCalibrator),
        transformer=fully_qualified_name(SigmoidFitTransformer),
        input_trans=False,
        output_trans=True,
    )
