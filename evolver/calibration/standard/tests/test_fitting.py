from datetime import datetime, timedelta

import numpy as np
import pytest
from pydantic import ValidationError

import evolver.settings
from evolver.base import ConfigDescriptor
from evolver.calibration.standard.polyfit import LinearCalibrator, LinearTransformer
from evolver.tests.conftest import tmp_calibration_dir  # noqa: F401


@pytest.fixture(scope="class")
def mock_linear_data():
    c = [10, 2]
    x = np.linspace(0, 100, 100)
    y = c[0] + x * c[1]
    return x, y, c


class TestLinearTransformer:
    def test_fit(self, mock_linear_data):
        x, y, c = mock_linear_data
        config = LinearTransformer.fit(x, y)
        assert config.degree == 1
        assert len(config.parameters) == 2
        assert config.parameters == pytest.approx(c)
        assert config.created - datetime.now() < timedelta(seconds=5)

    def test_convert(self, mock_linear_data):
        x, y, c = mock_linear_data
        obj = LinearTransformer(parameters=c)
        x_prime = 50
        y_prime = obj.convert_to(x_prime)
        assert y_prime == pytest.approx(c[0] + x_prime * c[1])
        assert obj.convert_from(y_prime) == pytest.approx(x_prime)

    def test_refit(self, mock_linear_data):
        x, y, c = mock_linear_data
        obj = LinearTransformer(parameters=c)
        old_config = obj.config_model
        assert obj.parameters == c
        c_prime = [c[0] + 2, c[1] + 3]
        y_prime = c_prime[0] + x * c_prime[1]
        new_config = obj.refit(x, y_prime)
        assert new_config.created > old_config.created
        assert new_config.parameters != old_config.parameters
        assert obj.parameters == pytest.approx(c_prime)

        x_prime = 50
        y_prime = obj.convert_to(x_prime)
        assert y_prime == pytest.approx(c_prime[0] + x_prime * c_prime[1])
        assert obj.convert_from(y_prime) == pytest.approx(x_prime)

    def test_validation(self, mock_linear_data):
        x, y, c = mock_linear_data
        with pytest.raises(ValidationError, match="Input should be less than or equal to 1"):
            LinearTransformer.Config(degree=2, parameters=c)

        with pytest.raises(ValidationError):
            LinearTransformer.Config(degree=1, parameters=[1, 2, 3])


class TestLinearCalibrator:
    def test_calibration_procedure(self, mock_linear_data, tmp_calibration_dir):  # noqa: F811
        x, y, c = mock_linear_data
        obj = LinearCalibrator(input_transformer=LinearTransformer(parameters=c))
        old_config = obj.input_transformer.config_model
        c_prime = [c[0] + 2, c[1] + 3]
        y_prime = c_prime[0] + x * c_prime[1]
        new_config = obj.run_calibration_procedure(dict(input_transformer=(x, y_prime)))["input_transformer"]

        assert new_config.created > old_config.created
        assert new_config.parameters != old_config.parameters
        assert new_config.parameters == pytest.approx(c_prime)

        x_prime = 50
        y_prime = obj.input_transformer.convert_to(x_prime)
        assert y_prime == pytest.approx(c_prime[0] + x_prime * c_prime[1])
        assert obj.input_transformer.convert_from(y_prime) == pytest.approx(x_prime)


class TestIndependentVialBasedLinearCalibrator:
    def test_config(self):
        descriptor = ConfigDescriptor.load(evolver.settings.settings.DEFAULT_TEMPERATURE_CALIBRATION_CONFIG_FILE)
        calibrator = descriptor.create()
        assert isinstance(calibrator.output_transformer, dict)
        assert evolver.settings.settings.DEFAULT_NUMBER_OF_VIALS_PER_BOX
        assert len(calibrator.output_transformer) == evolver.settings.settings.DEFAULT_NUMBER_OF_VIALS_PER_BOX
        for vial, transformer in calibrator.output_transformer.items():
            assert isinstance(transformer, LinearTransformer)
