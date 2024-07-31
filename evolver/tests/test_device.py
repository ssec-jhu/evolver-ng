import json

import pytest

import evolver.base
from evolver.calibration.interface import Calibrator, Status
from evolver.connection.interface import Connection
from evolver.controller.interface import Controller
from evolver.device import DEFAULT_HISTORY, DEFAULT_SERIAL, Evolver
from evolver.hardware.demo import NoOpSensorDriver
from evolver.hardware.interface import HardwareDriver
from evolver.history import History


@pytest.fixture
def conf_with_driver():
    return {
        "name": "evolver",
        "vials": [0, 1, 2, 3],
        "hardware": {
            "testsensor": {
                "classinfo": "evolver.hardware.demo.NoOpSensorDriver",
                "config": {"calibrator": {"classinfo": "evolver.calibration.demo.NoOpCalibrator", "config": {}}},
            },
            "testeffector": {"classinfo": "evolver.hardware.demo.NoOpEffectorDriver", "config": {}},
        },
        "controllers": [
            {"classinfo": "evolver.controller.demo.NoOpController", "config": {}},
        ],
        "serial": {"classinfo": "evolver.serial.EvolverSerialUARTEmulator"},
    }


@pytest.fixture
def demo_evolver(conf_with_driver):
    return Evolver.create(conf_with_driver)


class TestEvolver:
    def test_demo_evolver(self, demo_evolver, conf_with_driver):
        testsensor = demo_evolver.hardware["testsensor"]
        assert hasattr(testsensor, "calibrator")
        assert isinstance(testsensor.calibrator, Calibrator)

    def test_empty_config(self):
        obj = Evolver.Config()
        assert isinstance(obj, evolver.base.BaseConfig)
        assert isinstance(obj.serial, evolver.base.ConfigDescriptor)
        assert isinstance(obj.history, evolver.base.ConfigDescriptor)

    def test_instantiate_with_default_config(self):
        obj = Evolver.create()
        assert isinstance(obj, evolver.base.BaseInterface)
        assert isinstance(obj.serial, Connection)
        assert isinstance(obj.history, History)

    def test_instantiate_from_conf(self, conf_with_driver):
        obj = Evolver.create(conf_with_driver)
        assert isinstance(obj, Evolver)
        assert isinstance(obj.serial, Connection)
        assert isinstance(obj.hardware, dict)
        assert isinstance(obj.vials, list)
        assert isinstance(obj.controllers, list)

        for v in obj.hardware.values():
            assert isinstance(v, HardwareDriver)

        for item in obj.controllers:
            assert isinstance(item, Controller)

    def test_descriptor_serialization(self, conf_with_driver):
        obj = Evolver.create(conf_with_driver)
        obj.descriptor.model_dump_json()

    def test_config_correctness_from_conf(self, conf_with_driver):
        obj = Evolver.create(conf_with_driver)
        assert obj.config == obj.descriptor.config

        assert obj.config_json == json.dumps(obj.descriptor.config, separators=(",", ":"))
        obj2 = Evolver.create(obj.config_json)
        # Note: We can't just test obj.config_json == conf_with_driver because the latter contains empty sub-configs
        # and the former will contain sub-configs with default field values.
        assert obj2.config == obj.config
        assert obj2.config_json == obj.config_json

    def test_empty_config_property_equivalence(self):
        obj1 = Evolver.create()
        obj2 = Evolver.Config()
        assert obj1.config == obj2.model_dump(mode="json")

    def test_config_symmetry(self):
        obj1 = Evolver.create()
        obj2 = Evolver.create(obj1.config)
        assert obj1.config == obj2.config

    def test_config_symmetry_from_conf(self, conf_with_driver):
        obj1 = Evolver.create(conf_with_driver)
        obj2 = Evolver.create(obj1.config)
        assert obj1.config == obj2.config

    def test_with_driver(self, demo_evolver):
        assert isinstance(demo_evolver.hardware["testsensor"], NoOpSensorDriver)

    @pytest.mark.parametrize("method", ["read_state", "loop_once"])
    def test_read_and_get_state(self, demo_evolver, method):
        state = demo_evolver.state
        assert state["testsensor"] == {}
        getattr(demo_evolver, method)()
        state = demo_evolver.state
        for vial in demo_evolver.vials:
            assert state["testsensor"][vial] == NoOpSensorDriver.Output(vial=vial, raw=1, value=2)

    @pytest.mark.parametrize("enable_control", [True, False])
    def test_controller_control_in_loop_if_configured(self, demo_evolver, enable_control):
        assert demo_evolver.controllers[0].ncalls == 0
        demo_evolver.enable_control = enable_control
        demo_evolver.loop_once()
        assert demo_evolver.controllers[0].ncalls == (1 if enable_control else 0)

    def test_remove_driver(self, demo_evolver, conf_with_driver):
        assert "testeffector" in demo_evolver.hardware
        del conf_with_driver["hardware"]["testeffector"]
        obj = Evolver.create(conf_with_driver)
        assert "testeffector" not in obj.hardware

    def test_schema(self):
        Evolver.Config.model_json_schema()

    def test_non_descriptor_config_field(self):
        obj = Evolver(hardware={"a": NoOpSensorDriver()}, serial=DEFAULT_SERIAL(), history=DEFAULT_HISTORY())
        assert len(obj.hardware) == 1
        assert isinstance(obj.hardware["a"], NoOpSensorDriver)
        assert isinstance(obj.serial, DEFAULT_SERIAL)
        assert isinstance(obj.history, DEFAULT_HISTORY)

    def test_calibration_status(self, demo_evolver):
        status = demo_evolver.calibration_status
        assert status.keys() and (status.keys() == demo_evolver.hardware.keys())
        assert status["testeffector"] is None
        assert isinstance(status["testsensor"]["input_transformer"], Status)
        assert isinstance(status["testsensor"]["output_transformer"], Status)
