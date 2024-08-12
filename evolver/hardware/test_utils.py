import deepdiff

from evolver.base import ConfigDescriptor
from evolver.device import Evolver
from evolver.hardware.interface import HardwareDriver
from evolver.serial import create_mock_serial
from evolver.util import fully_qualified_name


def serial_from_response_map(response_map):
    """Return an EvolverSerialUART emulator from the given response map."""
    return create_mock_serial(response_map)


def evolver_from_response_map(response_map):
    """Return an evolver with attached serial from given response map."""
    return Evolver(serial=serial_from_response_map(response_map))


def _from_config_desc(driver, config, response_map):
    config_desc = ConfigDescriptor(classinfo=driver, config=config)
    return config_desc.create(non_config_kwargs={"evolver": evolver_from_response_map(response_map)})


def _from_evolver_conf(driver, config, response_map):
    evolver_config = {
        "hardware": {
            "testhw": {
                "classinfo": fully_qualified_name(driver),
                "config": config,
            }
        },
        "history": {
            "classinfo": "evolver.history.demo.InMemoryHistoryServer",
        },
    }
    evolver = Evolver.create(evolver_config)
    evolver.serial = serial_from_response_map(response_map)
    return evolver


class SerialVialSensorHardwareTestSuite:
    """Test suite for vial-based sensors using the evolver serial interface.

    Contains test for various creation patterns and asserts that outputs match expected
    given parametrized configurations. To use this suite, create a test class based on this,
    set the driver and parametrize the `response_map`, `config_params`, and `expected`
    variables, for ex::

        @pytest.mark.parametrize("response_map", [{b"serial_in": b"serial_out"}])
        @pytest.mark.parametrize("config_params, expected", [({"a": "b"}, Output(vial=0, raw=0))])
        class TestMySensor(SerialVialSensorHardwareTestSuite):
            driver = MySensorDriver

    where:
        * `response_map` is a mapping of serial input to serial output for the emulator
        * `config_params` is a dictionary of configuration for instantiating the driver
        * `expected` is the expected output, which will be checked by equality operator
    """

    driver: HardwareDriver = None

    def test_expected_create_from_config_desc(self, response_map, config_params, expected):
        hw = _from_config_desc(self.driver, config_params, response_map)
        hw.read()
        data = hw.get()
        assert not deepdiff.DeepDiff(data, expected, significant_digits=0)

    def test_expected_from_evolver_config(self, response_map, config_params, expected):
        evolver = _from_evolver_conf(self.driver, config_params, response_map)
        assert evolver.state == {"testhw": {}}
        evolver.loop_once()
        assert not deepdiff.DeepDiff(evolver.state, {"testhw": expected}, significant_digits=0)


class SerialVialEffectorHardwareTestSuite:
    """Test suite for vial-based effectors using the evolver serial interface.

    Contains test for various creation patterns and asserts that a serial command
    is submitted based on parametrized configs. To use this suite, create a test class
    based on this, set the driver and parametrize the `config_params`, `values` and
    `serial_out` variables, for ex::

        @pytest.mark.parametrize("config_params, values, serial_out",
            [({"a": "b"}, [[Input(vial=0, raw=0)]], [b"sent_serial"])])
        class TestMyEffector(SerialVialEffectorHardwareTestSuite):
            driver = MyEffectorDriver

    where:
        * `config_params` is a dictionary of configuration for instantiating the driver
        * `values` is a list of lists of Input values. The test will set values from and commit
          for each list and check against the corresponding index in `serial_out`. This enables
          to test persistence of previous inputs in case set is not specified for all vials.
        * `serial_out` is a list of the expected serial sent over the wire for the
          corresponding index in `values`.
    """

    driver: HardwareDriver = None

    def _load_and_check(self, hw, values, serial_out):
        expected_committed = {}
        assert len(serial_out) == len(values)
        for pair_i in range(len(serial_out)):
            for v in values[pair_i]:
                hw.set(v)
                if v.vial in hw.vials:
                    expected_committed[v.vial] = v
            hw.commit()
            assert hw.evolver.serial.backend.hits_map[serial_out[pair_i]] == 1
            # in case we expect multiple of same, clear for next assertion
            del hw.evolver.serial.backend.hits_map[serial_out[pair_i]]
            assert hw.committed == expected_committed

    def test_from_config_descriptor(self, config_params, values, serial_out):
        hw = _from_config_desc(self.driver, config_params, {})
        self._load_and_check(hw, values, serial_out)

    def test_from_evolver_config(self, config_params, values, serial_out):
        evolver = _from_evolver_conf(self.driver, config_params, {})
        self._load_and_check(evolver.hardware["testhw"], values, serial_out)
