from datetime import datetime, timedelta

import numpy as np
import pytest
from pydantic import ValidationError

from evolver.calibration.standard.polyfit import LinearCalibrator, LinearTransformer


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
        assert len(config.coefficients) == 2
        assert config.coefficients == pytest.approx(c)
        assert config.created - datetime.now() < timedelta(seconds=5)

    def test_convert(self, mock_linear_data):
        x, y, c = mock_linear_data
        obj = LinearTransformer(coefficients=c)
        x_prime = 50
        y_prime = obj.convert_to(x_prime)
        assert y_prime == pytest.approx(c[0] + x_prime * c[1])
        assert obj.convert_from(y_prime) == pytest.approx(x_prime)

    def test_refit(self, mock_linear_data):
        x, y, c = mock_linear_data
        obj = LinearTransformer(coefficients=c)
        old_config = obj.config_model
        assert obj.coefficients == c
        c_prime = [c[0] + 2, c[1] + 3]
        y_prime = c_prime[0] + x * c_prime[1]
        new_config = obj.refit(x, y_prime)
        assert new_config.created > old_config.created
        assert new_config.coefficients != old_config.coefficients
        assert obj.coefficients == pytest.approx(c_prime)

        x_prime = 50
        y_prime = obj.convert_to(x_prime)
        assert y_prime == pytest.approx(c_prime[0] + x_prime * c_prime[1])
        assert obj.convert_from(y_prime) == pytest.approx(x_prime)

    def test_validation(self, mock_linear_data):
        x, y, c = mock_linear_data
        with pytest.raises(ValidationError, match="Input should be less than or equal to 1"):
            LinearTransformer.Config(degree=2, coefficients=c)

        with pytest.raises(ValidationError):
            LinearTransformer.Config(degree=1, coefficients=[1, 2, 3])


class TestLinearCalibrator:
    def test_calibration_procedure(self, mock_linear_data):
        x, y, c = mock_linear_data
        obj = LinearCalibrator(input_transformer=LinearTransformer(coefficients=c))
        old_config = obj.input_transformer.config_model
        c_prime = [c[0] + 2, c[1] + 3]
        y_prime = c_prime[0] + x * c_prime[1]
        new_config = obj.run_calibration_procedure(dict(input_transformer=(x, y_prime)))["input_transformer"]

        assert new_config.created > old_config.created
        assert new_config.coefficients != old_config.coefficients
        assert new_config.coefficients == pytest.approx(c_prime)

        x_prime = 50
        y_prime = obj.input_transformer.convert_to(x_prime)
        assert y_prime == pytest.approx(c_prime[0] + x_prime * c_prime[1])
        assert obj.input_transformer.convert_from(y_prime) == pytest.approx(x_prime)
