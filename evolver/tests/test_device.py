import json
from unittest.mock import MagicMock

import pytest

import evolver.base
from evolver.calibration.interface import Calibrator, Status
from evolver.connection.interface import Connection
from evolver.controller.interface import Controller
from evolver.device import DEFAULT_HISTORY, DEFAULT_SERIAL, Evolver, Experiment
from evolver.hardware.demo import NoOpEffectorDriver, NoOpSensorDriver
from evolver.hardware.interface import EffectorDriver, HardwareDriver, SensorDriver
from evolver.history.interface import History


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
        "experiments": {
            "testA": {
                "controllers": [
                    {"classinfo": "evolver.controller.demo.NoOpController", "config": {}},
                ]
            },
            "testB": {
                "controllers": [
                    {"classinfo": "evolver.controller.demo.NoOpController", "config": {}},
                ]
            },
        },
        "serial": {"classinfo": "evolver.serial.EvolverSerialUARTEmulator"},
        "history": {"classinfo": "evolver.history.demo.InMemoryHistoryServer"},
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
        assert isinstance(obj.experiments, dict)

        for v in obj.hardware.values():
            assert isinstance(v, HardwareDriver)

        for item in obj.experiments.values():
            assert isinstance(item, Experiment)

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
        assert obj1.config == obj2.model_dump(mode="json")["config"]

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
            assert state["testsensor"][vial] == NoOpSensorDriver.Output(
                vial=vial, raw=1, value=2, name="NoOpSensorDriver"
            )

    @pytest.mark.parametrize("enable_control", [True, False])
    def test_controller_control_in_loop_if_configured(self, demo_evolver, enable_control):
        assert demo_evolver.enabled_controllers[0].ncalls == 0
        demo_evolver.enable_control = enable_control
        demo_evolver.loop_once()
        assert demo_evolver.enabled_controllers[0].ncalls == (1 if enable_control else 0)

    def test_experiment_enable_switch_and_enabled_controllers(self, demo_evolver):
        # We don't otherwise make any guarantees of the order of experiments,
        # however we do expect the deserialization and python dict to preserve
        # order, so "testA" + "testB" is at least somewhat intentional (as
        # opposed to using sorted)
        assert (
            demo_evolver.enabled_controllers
            == demo_evolver.experiments["testA"].controllers + demo_evolver.experiments["testB"].controllers
        )
        demo_evolver.loop_once()
        assert demo_evolver.experiments["testA"].controllers[0].ncalls == 1
        assert demo_evolver.experiments["testB"].controllers[0].ncalls == 1
        demo_evolver.experiments["testA"].enabled = False
        assert demo_evolver.enabled_controllers == demo_evolver.experiments["testB"].controllers
        demo_evolver.loop_once()
        assert demo_evolver.experiments["testA"].controllers[0].ncalls == 1
        assert demo_evolver.experiments["testB"].controllers[0].ncalls == 2

    @pytest.mark.parametrize("spec", [SensorDriver, EffectorDriver, Controller])
    def test_loop_exception_option(self, demo_evolver, spec):
        demo_evolver.raise_loop_exceptions = True
        raises_mock_component = MagicMock(spec=spec)
        if spec == Controller:
            demo_evolver.experiments = {"test": MagicMock(enabled=True, controllers=[raises_mock_component])}
            raises_mock_component.run = MagicMock(side_effect=Exception("test control"))
        else:
            demo_evolver.hardware["testsensor"] = raises_mock_component
            raises_mock_component.read = MagicMock(side_effect=Exception("test read"))
            raises_mock_component.commit = MagicMock(side_effect=Exception("test commit"))
        with pytest.raises(Exception, match="test .*"):
            demo_evolver.loop_once()
        demo_evolver.raise_loop_exceptions = False
        demo_evolver.loop_once()

    def test_skip_control_on_read_failure(self, demo_evolver):
        demo_evolver.skip_control_on_read_failure = True
        demo_evolver.hardware["testsensor"].read = MagicMock(side_effect=Exception("test read"))
        mock_controller = MagicMock(spec=Controller)
        demo_evolver.experiments = {"test": MagicMock(controllers=[mock_controller])}
        demo_evolver.loop_once()
        mock_controller.run.assert_not_called()
        demo_evolver.skip_control_on_read_failure = False
        demo_evolver.loop_once()
        mock_controller.run.assert_called_once()

    def test_abort_on_control_failure(self, demo_evolver):
        demo_evolver.abort_on_control_errors = True
        mock_controller = MagicMock(spec=Controller)
        mock_controller.run = MagicMock(side_effect=Exception("test control"))
        demo_evolver.experiments = {"test": MagicMock(controllers=[mock_controller])}
        mock_hardware = MagicMock(spec=EffectorDriver)
        demo_evolver.hardware["testsensor"] = mock_hardware
        assert demo_evolver.enable_control
        with pytest.raises(RuntimeError, match="Aborted due to control error"):
            demo_evolver.loop_once()
        # aborts effect is to turn off the control flag and call off on all effectors
        assert not demo_evolver.enable_control
        mock_hardware.off.assert_called_once()

    def test_abort_on_commit_failure(self, demo_evolver):
        demo_evolver.abort_on_commit_errors = True
        mock_hardware = MagicMock(spec=EffectorDriver)
        demo_evolver.hardware["testeffector"] = mock_hardware
        mock_hardware.commit = MagicMock(side_effect=Exception("test commit"))
        assert demo_evolver.enable_control
        with pytest.raises(RuntimeError, match="Aborted due to commit error"):
            demo_evolver.loop_once()
        assert not demo_evolver.enable_control
        mock_hardware.off.assert_called_once()

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
        assert isinstance(status["testsensor"], Calibrator.Status)
        assert isinstance(status["testsensor"].input_transformer, Status)
        assert isinstance(status["testsensor"].output_transformer, Status)
        assert status["testsensor"].ok

    def test_abort(self, demo_evolver):
        class AbortEffector(NoOpEffectorDriver):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.aborted = False

            def off(self):
                super().off()
                self.aborted = True

        demo_evolver.hardware["testeffector"] = AbortEffector()
        demo_evolver.enable_control = True
        assert demo_evolver.enable_control
        demo_evolver.abort()
        assert not demo_evolver.enable_control
        assert demo_evolver.hardware["testeffector"].aborted
        assert not demo_evolver.enable_control

    def test_vials_layout_validation(self):
        with pytest.raises(ValueError, match="Vials configured exceed total available slots"):
            Evolver.Config(vials=[0, 1, 2, 3, 4], vial_layout=[2, 2])
        with pytest.raises(ValueError, match="Vials configured exceed total available slots"):
            Evolver.Config(vials=[0, 1, 2, 8], vial_layout=[2, 2])
        Evolver.Config(vials=[0, 1, 2, 3], vial_layout=[2, 2])
