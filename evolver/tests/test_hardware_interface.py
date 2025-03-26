import pytest

from evolver.hardware.interface import EffectorDriver


def test_effector_driver_set():
    class TestEffectorDriver(EffectorDriver):
        class Input(EffectorDriver.Input):
            value_a: float
            value_b: float = 0.0

        def commit(self):
            pass

        def off(self):
            pass

    driver = TestEffectorDriver()
    driver.set(vial=0, value_a=1.0)
    assert driver.proposal == {0: TestEffectorDriver.Input(vial=0, value_a=1.0)}

    driver = TestEffectorDriver()
    with pytest.raises(ValueError):  # needs vial
        driver.set(value_a=1.0, value_b=2.0)

    driver = TestEffectorDriver()
    driver.set(TestEffectorDriver.Input(vial=0, value_a=1.0))
    assert driver.proposal == {0: TestEffectorDriver.Input(vial=0, value_a=1.0)}

    driver = TestEffectorDriver()
    with pytest.raises(ValueError):  # shouldn't be allowed to mix
        driver.set(TestEffectorDriver.Input(vial=0, value_a=1.0), vial=0, value_a=1, value_b=2.0)

    driver = TestEffectorDriver()
    with pytest.raises(ValueError):  # needs input
        driver.set()
