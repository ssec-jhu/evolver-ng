from unittest.mock import MagicMock

import pytest

from evolver.controller.interface import Controller
from evolver.device import Evolver


class TestController(Controller):
    def pre_control(self, *args, **kwargs):
        return "pre control data"

    def control(self, *args, pre_control_output=None, **kwargs):
        assert pre_control_output == "pre control data"
        return pre_control_output + ", control data"

    def post_control(self, *args, control_output=None, **kwargs):
        assert control_output == "pre control data, control data"
        return control_output + ", post control data"


class TestControllerInterface:
    def test_hooks(self):
        assert TestController(evolver=None).run() == "pre control data, control data, post control data"

    def test_get_hw(self):
        sensor_mock = MagicMock()
        evolver = Evolver(hardware={"sensor": sensor_mock})
        controller = TestController(evolver=evolver)
        # for strings we expect the hardware attached to evolver manager
        assert controller.get_hw("sensor") == sensor_mock
        with pytest.raises(KeyError):
            controller.get_hw("nonexistent_sensor")

        # for hardware passed directly, we return the same object and do not
        # consult the evolver manager
        direct_hw_mock = MagicMock()
        assert controller.get_hw(direct_hw_mock) == direct_hw_mock
