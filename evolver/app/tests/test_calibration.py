from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from evolver.app.main import app
from evolver.calibration.demo import NoOpCalibrator
from evolver.calibration.standard.calibrators.temperature import TemperatureCalibrator
from evolver.calibration.standard.polyfit import LinearTransformer
from evolver.device import Evolver
from evolver.hardware.demo import NoOpSensorDriver
from evolver.tests.conftest import tmp_calibration_dir  # noqa: F401


def setup_evolver_with_calibrator(calibrator_class, hardware_name="test", vials=[0, 1, 2], procedure_file=None):
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
        procedure_file=procedure_file,
    )
    evolver_instance = Evolver(
        hardware={hardware_name: NoOpSensorDriver(name=hardware_name, calibrator=calibrator, vials=vials)}
    )
    calibrator.evolver = evolver_instance
    app.state.evolver = evolver_instance
    return calibrator, TestClient(app)


def get_empty_calibration_state():
    """Return the expected subset for an empty/reset calibration state."""
    return {"completed_actions": [], "history": [], "measured": {}, "started": True}


def dispatch_action(client, hardware_name, action_name, payload=None):
    return client.post(
        f"/hardware/{hardware_name}/calibrator/procedure/dispatch",
        json={"action_name": action_name, "payload": payload or {}},
    )


class TestCalibration:
    def test_get_calibration_status(self):
        _, client = setup_evolver_with_calibrator(NoOpCalibrator)

        response = client.post("/hardware/test/calibrator/procedure/start", params={"resume": False})
        assert response.status_code == 200

        response = client.get("/hardware/test/calibrator/procedure/state")
        assert response.status_code == 200

        response_data = response.json()
        # Assert the fixed fields we care about
        expected_subset = {"completed_actions": [], "history": [], "measured": {}, "started": True}
        assert expected_subset.items() <= response_data.items()

        # Assert schema without checking specific values
        required_fields = {"created", "dir", "expire", "name"}
        assert all(field in response_data for field in required_fields)

    def test_get_calibration_status_not_started(self):
        _, client = setup_evolver_with_calibrator(NoOpCalibrator)

        response = client.get("/hardware/test/calibrator/procedure/state")
        assert response.status_code == 200
        assert response.json() == {"started": False}


def test_temperature_calibration_procedure_actions():
    temp_calibrator, client = setup_evolver_with_calibrator(TemperatureCalibrator)

    response = client.post("/hardware/test/calibrator/procedure/start", params={"resume": False})
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


def test_temperature_calibration_procedure_actions_not_started():
    temp_calibrator, client = setup_evolver_with_calibrator(TemperatureCalibrator)

    response = client.get("/hardware/test/calibrator/procedure/actions")
    assert response.status_code == 200
    assert response.json() == {"started": False}


def test_dispatch_temperature_calibration_bad_reference_value_action():
    _, client = setup_evolver_with_calibrator(TemperatureCalibrator)

    client.post("/hardware/test/calibrator/procedure/start", params={"resume": False})

    action_payload = {"action_name": "measure_vial_0_temperature", "payload": {"this_should_not_work": 25.0}}
    dispatch_response = dispatch_action(client, "test", "measure_vial_0_temperature", action_payload["payload"])

    assert dispatch_response.status_code == 422


def test_dispatch_temperature_calibration_raw_value_action():
    _, client = setup_evolver_with_calibrator(TemperatureCalibrator)

    app.state.evolver.hardware["test"].read = lambda: [1.23, 2.34, 3.45]

    client.post("/hardware/test/calibrator/procedure/start", params={"resume": False})

    raw_dispatch_response = dispatch_action(client, "test", "read_vial_0_raw_output")

    assert raw_dispatch_response.status_code == 200

    response_data = raw_dispatch_response.json()
    initial_state = response_data["history"][0]  # Get the actual initial state from history

    expected_subset = {
        "completed_actions": ["read_vial_0_raw_output"],
        "history": [initial_state],  # Use the actual initial state with all fields
        "measured": {"0": {"raw": [1.23], "reference": []}},
        "started": True,
    }
    assert expected_subset.items() <= raw_dispatch_response.json().items()


def test_reset_calibration_procedure():
    _, client = setup_evolver_with_calibrator(TemperatureCalibrator)

    app.state.evolver.hardware["test"].read = lambda: [1.23, 2.34, 3.45]

    client.post("/hardware/test/calibrator/procedure/start", params={"resume": False})

    raw_dispatch_response = dispatch_action(client, "test", "read_vial_0_raw_output")
    assert raw_dispatch_response.status_code == 200

    reset_response = client.post("/hardware/test/calibrator/procedure/start", params={"resume": False})
    assert reset_response.status_code == 200

    expected_subset = get_empty_calibration_state()
    assert expected_subset.items() <= reset_response.json().items()


def test_calibration_procedure_undo_action_utility():
    _, client = setup_evolver_with_calibrator(TemperatureCalibrator)

    app.state.evolver.hardware["test"].read = lambda: [1.23, 2.34, 3.45]

    client.post("/hardware/test/calibrator/procedure/start", params={"resume": False})

    dispatch_response = dispatch_action(client, "test", "read_vial_0_raw_output")
    assert dispatch_response.status_code == 200

    undo_response = client.post("/hardware/test/calibrator/procedure/undo")
    assert undo_response.status_code == 200

    expected_subset = get_empty_calibration_state()
    assert expected_subset.items() <= undo_response.json().items()


def test_calibration_procedure_save(tmp_path):
    # Setup fs for save.
    cal_file = tmp_path / "calibration.yml"

    _, client = setup_evolver_with_calibrator(TemperatureCalibrator, procedure_file=str(cal_file))
    app.state.evolver.hardware["test"].read = lambda: [1.23, 2.34, 3.45]

    # Start procedure
    client.post("/hardware/test/calibrator/procedure/start", params={"resume": False})

    # Dispatch an action to have something to save
    dispatch_response = dispatch_action(client, "test", "read_vial_0_raw_output")
    assert dispatch_response.status_code == 200

    # Test successful save
    save_response = client.post("/hardware/test/calibrator/procedure/save")
    assert save_response.status_code == 200

    response_data = save_response.json()
    initial_state = response_data["history"][0]  # Get the actual initial state
    expected_subset = {
        "completed_actions": ["read_vial_0_raw_output"],
        "history": [initial_state],
        "measured": {"0": {"raw": [1.23], "reference": []}},
        "started": True,
    }
    assert expected_subset.items() <= response_data.items()

    # Test save with no calibrator
    no_calibrator_response = client.post("/hardware/nonexistent/calibrator/procedure/save")
    assert no_calibrator_response.status_code == 404

    # Test save with no procedure started
    app.state.evolver.hardware["test"].calibrator.calibration_procedure = None
    no_procedure_response = client.post("/hardware/test/calibrator/procedure/save")
    assert no_procedure_response.json() == {"started": False}

    # Test save failure
    app.state.evolver.hardware["test"].calibrator.calibration_procedure = MagicMock()
    app.state.evolver.hardware["test"].calibrator.calibration_procedure.save.side_effect = Exception
    error_response = client.post("/hardware/test/calibrator/procedure/save")
    assert error_response.status_code == 500


def test_calibration_procedure_resume(tmp_path):
    # Setup fs for save
    cal_file = tmp_path / "calibrationXXX.yml"

    # Initial setup and procedure
    _, client = setup_evolver_with_calibrator(TemperatureCalibrator, procedure_file=str(cal_file))
    app.state.evolver.hardware["test"].read = lambda: [1.23, 2.34, 3.45]

    # Start and perform initial procedure actions
    client.post("/hardware/test/calibrator/procedure/start", params={"resume": False})
    dispatch_response = dispatch_action(client, "test", "read_vial_0_raw_output")
    assert dispatch_response.status_code == 200

    # Save procedure state
    save_response = client.post("/hardware/test/calibrator/procedure/save")
    assert save_response.status_code == 200
    saved_state = save_response.json()

    # Create new client to simulate fresh start
    _, new_client = setup_evolver_with_calibrator(TemperatureCalibrator, procedure_file=str(cal_file))

    # Resume procedure
    resume_response = new_client.post("/hardware/test/calibrator/procedure/start", params={"resume": True})
    assert resume_response.status_code == 200

    # Extract the core fields we want to compare from both states
    resume_data = resume_response.json()
    expected_subset = {
        "completed_actions": saved_state["completed_actions"],
        "history": saved_state["history"],  # This includes all fields from saved state
        "measured": saved_state["measured"],
        "started": saved_state["started"],
    }
    assert expected_subset.items() <= resume_data.items()


def test_dispatch_temperature_calibration_calculate_fit_action():
    temp_calibrator, client = setup_evolver_with_calibrator(TemperatureCalibrator)

    app.state.evolver.hardware["test"].read = lambda: [1.23, 2.34, 3.45]

    client.post("/hardware/test/calibrator/procedure/start", params={"resume": False})

    reference_dispatch_response = dispatch_action(client, "test", "measure_vial_0_temperature", {"temperature": 25.0})
    assert reference_dispatch_response.status_code == 200

    raw_dispatch_response = dispatch_action(client, "test", "read_vial_0_raw_output")
    assert raw_dispatch_response.status_code == 200

    fit_dispatch_response = dispatch_action(client, "test", "calculate_vial_0_fit")
    assert fit_dispatch_response.status_code == 200

    output_transformer_response = client.get("/hardware/test/calibrator/output_transformer")
    assert output_transformer_response.status_code == 200
    assert output_transformer_response.json()["0"]["parameters"] == [0.6149999999999997, 0.024599999999999997]


def get_stable_state_subset(state):
    """Extract only the stable fields we want to compare from a state object."""
    result = {
        "completed_actions": state["completed_actions"],
        "history": [],
        "measured": state["measured"],
        "started": state["started"],
    }

    # Recursively process history
    if state["history"]:
        result["history"] = [get_stable_state_subset(h) for h in state["history"]]

    return result


def test_get_calibration_data(tmp_path):
    # Setup fs for save.
    cal_file = tmp_path / "calibration.yml"

    temp_calibrator, client = setup_evolver_with_calibrator(TemperatureCalibrator, procedure_file=str(cal_file))

    app.state.evolver.hardware["test"].read = lambda: [1.23, 2.34, 3.45]

    client.post("/hardware/test/calibrator/procedure/start", params={"resume": False})

    dispatch_action(client, "test", "measure_vial_0_temperature", {"temperature": 25.0})
    dispatch_action(client, "test", "read_vial_0_raw_output")
    dispatch_action(client, "test", "calculate_vial_0_fit")

    # save the calibration data, this pops the data up into the calibrator's CalibrationData class.
    save_response = client.post("/hardware/test/calibrator/procedure/save")
    assert save_response.status_code == 200

    calibration_data_response = client.get("/hardware/test/calibrator/data")
    assert calibration_data_response.status_code == 200
    calibration_data = calibration_data_response.json()

    # Extract only the stable fields we want to compare
    actual_state = get_stable_state_subset(calibration_data)

    expected_state = {
        "completed_actions": ["measure_vial_0_temperature", "read_vial_0_raw_output", "calculate_vial_0_fit"],
        "history": [
            {"completed_actions": [], "history": [], "measured": {}, "started": True},
            {
                "completed_actions": ["measure_vial_0_temperature"],
                "history": [{"completed_actions": [], "history": [], "measured": {}, "started": True}],
                "measured": {"0": {"raw": [], "reference": [25.0]}},
                "started": True,
            },
            {
                "completed_actions": ["measure_vial_0_temperature", "read_vial_0_raw_output"],
                "history": [
                    {"completed_actions": [], "history": [], "measured": {}, "started": True},
                    {
                        "completed_actions": ["measure_vial_0_temperature"],
                        "history": [{"completed_actions": [], "history": [], "measured": {}, "started": True}],
                        "measured": {"0": {"raw": [], "reference": [25.0]}},
                        "started": True,
                    },
                ],
                "measured": {"0": {"raw": [1.23], "reference": [25.0]}},
                "started": True,
            },
        ],
        "measured": {"0": {"raw": [1.23], "reference": [25.0]}},
        "started": True,
    }

    assert actual_state == expected_state
