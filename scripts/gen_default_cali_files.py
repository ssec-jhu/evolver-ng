from datetime import datetime

import requests

from evolver.base import ConfigDescriptor
from evolver.calibration.standard.polyfit import IndependentVialBasedLinearCalibrator, LinearTransformer
from evolver.settings import settings
from evolver.util import fully_qualified_name


def temperature_file(filename, url, timestamp):
    data = requests.get(url).json()

    coefficients = data[1]["fits"][0]["coefficients"]

    descriptor = ConfigDescriptor(
        classinfo=fully_qualified_name(IndependentVialBasedLinearCalibrator),
        config={
            "output_transformer": {
                vial: ConfigDescriptor(
                    classinfo=fully_qualified_name(LinearTransformer),
                    config={"coefficients": coeffs[::-1], "created": timestamp},
                )
                for vial, coeffs in enumerate(coefficients)
            },
            "input_transformer": {
                vial: ConfigDescriptor(
                    classinfo=fully_qualified_name(LinearTransformer),
                    config={"coefficients": coeffs[::-1], "created": timestamp},
                )
                for vial, coeffs in enumerate(coefficients)
            },
        },
    )
    descriptor.save(filename)


if __name__ == "__main__":
    temperature_file(
        filename=settings.DEFAULT_TEMPERATURE_CALIBRATION_CONFIG_FILE,
        url="https://raw.githubusercontent.com/FYNCH-BIO/evolver/master/evolver/calibrations.json",
        # There doesn't seem to be a concrete format that makes it worth parsing stuff, so we just set here explicitly.
        timestamp=datetime(year=2019, month=2, day=1),
    )
