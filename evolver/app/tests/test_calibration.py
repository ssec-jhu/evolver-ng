from fastapi.testclient import TestClient

from evolver.app.main import app
from evolver.calibration.demo import NoOpCalibrator
from evolver.calibration.standard.calibrators.temperature import TemperatureCalibrator
from evolver.calibration.standard.polyfit import LinearTransformer
from evolver.device import Evolver
from evolver.hardware.demo import NoOpSensorDriver
from evolver.tests.conftest import tmp_calibration_dir  # noqa: F401


def setup_evolver_with_calibrator(calibrator_class, hardware_name="test", vials=[0, 1, 2]):
    calibrator = calibrator_class(
        input_transformer={
            0: LinearTransformer("Test Transformer"),
            1: LinearTransformer(),
            2: LinearTransformer(),
        },
        output_transformer={
            0: LinearTransformer(),
            1: LinearTransformer(),
            2: LinearTransformer(),
        },
    )
    evolver_instance = Evolver(
        hardware={hardware_name: NoOpSensorDriver(name=hardware_name, calibrator=calibrator, vials=vials)}
    )
    calibrator.evolver = evolver_instance
    app.state.evolver = evolver_instance
    return calibrator, TestClient(app)


def dispatch_action(client, hardware_name, action_name, payload=None):
    return client.post(
        f"/hardware/{hardware_name}/calibrator/procedure/dispatch",
        json={"action_name": action_name, "payload": payload or {}},
    )


class TestCalibration:
    def test_get_calibration_status(self):
        _, client = setup_evolver_with_calibrator(NoOpCalibrator)

        response = client.post("/hardware/test/calibrator/procedure/start")
        assert response.status_code == 200

        response = client.get("/hardware/test/calibrator/procedure/state")
        assert response.status_code == 200
        assert response.json() == {"completed_actions": []}


def test_temperature_calibration_procedure_actions():
    temp_calibrator, client = setup_evolver_with_calibrator(TemperatureCalibrator)

    response = client.post("/hardware/test/calibrator/procedure/start")
    assert response.status_code == 200

    actions_response = client.get("/hardware/test/calibrator/procedure/actions")
    assert actions_response.status_code == 200

    expected_actions = [
        {
            "name": action.name,
            "description": action.description,
            "input_schema": action.FormModel.schema() if action.FormModel else None,
        }
        for action in temp_calibrator.calibration_procedure.actions
    ]

    actual_actions = actions_response.json()["actions"]
    assert len(actual_actions) == len(expected_actions)
    for expected_action in expected_actions:
        assert expected_action in actual_actions


def test_dispatch_temperature_calibration_bad_reference_value_action():
    _, client = setup_evolver_with_calibrator(TemperatureCalibrator)

    client.post("/hardware/test/calibrator/procedure/start")

    action_payload = {"action_name": "measure_vial_0_temperature", "payload": {"this_should_not_work": 25.0}}
    dispatch_response = dispatch_action(client, "test", "measure_vial_0_temperature", action_payload["payload"])

    assert dispatch_response.status_code == 422


def test_dispatch_temperature_calibration_raw_value_action():
    _, client = setup_evolver_with_calibrator(TemperatureCalibrator)

    app.state.evolver.hardware["test"].read = lambda: [1.23, 2.34, 3.45]

    client.post("/hardware/test/calibrator/procedure/start")

    raw_dispatch_response = dispatch_action(client, "test", "read_vial_0_raw_output")

    assert raw_dispatch_response.status_code == 200
    assert raw_dispatch_response.json() == {
        "0": {"reference": [], "raw": [1.23]},
        "completed_actions": ["read_vial_0_raw_output"],
    }


def test_reset_calibration_procedure():
    _, client = setup_evolver_with_calibrator(TemperatureCalibrator)

    app.state.evolver.hardware["test"].read = lambda: [1.23, 2.34, 3.45]

    client.post("/hardware/test/calibrator/procedure/start")

    raw_dispatch_response = dispatch_action(client, "test", "read_vial_0_raw_output")
    assert raw_dispatch_response.status_code == 200

    reset_response = client.post("/hardware/test/calibrator/procedure/start", json={"resume": False})
    assert reset_response.status_code == 200
    assert reset_response.json() == {"completed_actions": []}


def test_calibration_procedure_undo_action_utility():
    _, client = setup_evolver_with_calibrator(TemperatureCalibrator)

    app.state.evolver.hardware["test"].read = lambda: [1.23, 2.34, 3.45]

    client.post("/hardware/test/calibrator/procedure/start")

    dispatch_response = dispatch_action(client, "test", "read_vial_0_raw_output")
    assert dispatch_response.status_code == 200

    undo_response = client.post("/hardware/test/calibrator/procedure/undo")
    assert undo_response.status_code == 200
    assert undo_response.json() == {"completed_actions": []}


def test_dispatch_temperature_calibration_calculate_fit_action():
    temp_calibrator, client = setup_evolver_with_calibrator(TemperatureCalibrator)

    app.state.evolver.hardware["test"].read = lambda: [1.23, 2.34, 3.45]

    client.post("/hardware/test/calibrator/procedure/start")

    reference_dispatch_response = dispatch_action(client, "test", "measure_vial_0_temperature", {"temperature": 25.0})
    assert reference_dispatch_response.status_code == 200

    raw_dispatch_response = dispatch_action(client, "test", "read_vial_0_raw_output")
    assert raw_dispatch_response.status_code == 200

    fit_dispatch_response = dispatch_action(client, "test", "calculate_vial_0_fit")
    assert fit_dispatch_response.status_code == 200

    output_transformer_response = client.get("/hardware/test/calibrator/output_transformer")
    assert output_transformer_response.status_code == 200
    assert output_transformer_response.json()["0"]["parameters"] == [0.6149999999999997, 0.024599999999999997]


def test_get_calibration_data():
    temp_calibrator, client = setup_evolver_with_calibrator(TemperatureCalibrator)

    app.state.evolver.hardware["test"].read = lambda: [1.23, 2.34, 3.45]

    client.post("/hardware/test/calibrator/procedure/start")

    dispatch_action(client, "test", "measure_vial_0_temperature", {"temperature": 25.0})
    dispatch_action(client, "test", "read_vial_0_raw_output")
    dispatch_action(client, "test", "calculate_vial_0_fit")
    dispatch_action(client, "test", "save_calibration_procedure_state")

    calibration_data_response = client.get("/hardware/test/calibrator/data")
    assert calibration_data_response.status_code == 200
    calibration_data = calibration_data_response.json()

    assert calibration_data["measured"] == {
        "0": {
            "raw": [1.23],
            "reference": [25.0],
        },
        "completed_actions": [
            "measure_vial_0_temperature",
            "read_vial_0_raw_output",
            "calculate_vial_0_fit",
            "save_calibration_procedure_state",
        ],
    }
