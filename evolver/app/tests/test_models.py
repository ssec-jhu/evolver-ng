import pytest

import evolver.util
from evolver.app.models import SchemaResponse
from evolver.base import BaseInterface
from evolver.device import Evolver
from evolver.hardware.demo import NoOpCalibrator, NoOpEffectorDriver, NoOpSensorDriver
from evolver.hardware.interface import EffectorDriver, SensorDriver


@pytest.mark.parametrize(
    "classinfo",
    (
        Evolver,
        BaseInterface,
        EffectorDriver,
        SensorDriver,
        NoOpCalibrator,
        NoOpEffectorDriver,
        NoOpSensorDriver,
    ),
)
def test_schema_response(classinfo):
    fqn = evolver.util.fully_qualified_name(classinfo)
    obj = SchemaResponse(classinfo=fqn)
    assert obj.config == classinfo.Config.model_json_schema()
    assert obj.classinfo is classinfo
    if hasattr(classinfo, "Input"):
        assert obj.input == classinfo.Input.model_json_schema()
    else:
        assert obj.input is None
    if hasattr(classinfo, "Output"):
        assert obj.output == classinfo.Output.model_json_schema()
    else:
        assert obj.output is None
