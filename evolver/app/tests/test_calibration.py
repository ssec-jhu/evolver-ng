from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from evolver.app.main import app
from evolver.calibration.demo import NoOpCalibrator, NoOpPerVialCalibrator
from evolver.calibration.standard.calibrators.temperature import TemperatureCalibrator
from evolver.calibration.standard.polyfit import LinearTransformer
from evolver.device import Evolver
from evolver.hardware.demo import NoOpSensorDriver
from evolver.settings import app_settings
from evolver.tests.conftest import tmp_calibration_dir  # noqa: F401


def setup_evolver_with_calibrator(
    calibrator_class, hardware_name="test", vials=[0, 1, 2], procedure_file=None, calibration_file=None
):
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
        calibration_file=calibration_file,
    )
    evolver_instance = Evolver(
        hardware={hardware_name: NoOpSensorDriver(name=hardware_name, calibrator=calibrator, vials=vials)}
    )
    calibrator.evolver = evolver_instance
    app.state.evolver = evolver_instance
    return calibrator, TestClient(app)


def get_empty_calibration_state():
    """Return the expected subset for an empty/reset calibration state."""
    return {"completed_actions": [], "history": [], "measured": {}}


def dispatch_action(client, hardware_name, action_name, payload=None):
    return client.post(
        f"/hardware/{hardware_name}/calibrator/procedure/dispatch",
        json={"action_name": action_name, "payload": payload or {}},
    )


class TestCalibration:
    def test_get_calibration_status(self, tmp_path):
        _, client = setup_evolver_with_calibrator(NoOpPerVialCalibrator)

        procedure_file = str(tmp_path / "my_test_calibration_procedure.yml")
        response = client.post(
            "/hardware/test/calibrator/procedure/start",
            params={"procedure_file": procedure_file},
        )
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


def test_temperature_calibration_procedure_actions(tmp_path):
    temp_calibrator, client = setup_evolver_with_calibrator(TemperatureCalibrator)

    procedure_file = str(tmp_path / "my_test_calibration_procedure.yml")
    response = client.post(
        "/hardware/test/calibrator/procedure/start",
        params={"procedure_file": procedure_file},
    )

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


def test_dispatch_temperature_calibration_bad_reference_value_action(tmp_path):
    _, client = setup_evolver_with_calibrator(TemperatureCalibrator)

    procedure_file = str(tmp_path / "my_test_calibration_procedure.yml")
    client.post(
        "/hardware/test/calibrator/procedure/start",
        params={"procedure_file": procedure_file},
    )

    action_payload = {"action_name": "measure_vial_0_temperature", "payload": {"this_should_not_work": 25.0}}
    dispatch_response = dispatch_action(client, "test", "measure_vial_0_temperature", action_payload["payload"])

    assert dispatch_response.status_code == 422


def test_dispatch_temperature_calibration_raw_value_action(tmp_path):
    _, client = setup_evolver_with_calibrator(TemperatureCalibrator)

    app.state.evolver.hardware["test"].read = lambda: [1.23, 2.34, 3.45]

    procedure_file = str(tmp_path / "my_test_calibration_procedure.yml")
    client.post(
        "/hardware/test/calibrator/procedure/start",
        params={"procedure_file": procedure_file},
    )

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


def test_start_calibration_no_procedure_file(tmp_path, monkeypatch):
    monkeypatch.setattr(app_settings, "CONFIG_FILE", str(tmp_path / "evolver.yml"))
    _, client = setup_evolver_with_calibrator(TemperatureCalibrator)
    client.post("/hardware/test/calibrator/procedure/start", params={"resume": False})


def test_reset_calibration_procedure(tmp_path):
    temp_calibrator, client = setup_evolver_with_calibrator(TemperatureCalibrator)
    app.state.evolver.hardware["test"].read = lambda: [1.23, 2.34, 3.45]

    procedure_file = str(tmp_path / "my_test_calibration_procedure.yml")
    start_response = client.post(
        "/hardware/test/calibrator/procedure/start",
        params={"procedure_file": procedure_file},
    )
    assert start_response.status_code == 200
    assert temp_calibrator.procedure_file == procedure_file

    # Remember the first procedure file
    first_procedure_file = temp_calibrator.procedure_file

    # Perform an action
    raw_dispatch_response = dispatch_action(client, "test", "read_vial_0_raw_output")
    assert raw_dispatch_response.status_code == 200

    # Reset procedure and check if a new procedure file is generated
    new_procedure_file = str(tmp_path / "my_test_calibration_procedure_2.yml")
    reset_response = client.post(
        "/hardware/test/calibrator/procedure/start",
        params={"procedure_file": new_procedure_file},
    )
    assert reset_response.status_code == 200

    # Verify the new updated / new procedure_file is not the same as the (1-sec-ago) old one
    assert temp_calibrator.procedure_file != first_procedure_file


def test_calibration_procedure_resume_with_no_procedure_file():
    # Test resuming when no procedure file exists yet
    temp_calibrator, client = setup_evolver_with_calibrator(TemperatureCalibrator)

    # Ensure procedure_file is None initially
    assert temp_calibrator.procedure_file is None

    # Try to resume - should fail with a 404 and a clear error message
    resume_response = client.post("/hardware/test/calibrator/procedure/resume")
    assert resume_response.status_code == 404
    assert "No in progress calibration procedure was found" in resume_response.json()["detail"]


def test_calibration_procedure_resume_with_existing_procedure_file(tmp_path):
    # Setup fs for an existing calibration_procedure_file.
    procedure_file = str(tmp_path / "my_test_calibration_procedure.yml")

    # create a file at cal_file, because this is created in tmp_path pytest handles cleanup.
    from pathlib import Path

    Path(procedure_file).touch()

    # Initial setup using the existing calibration_procedure file
    temp_calibrator, client = setup_evolver_with_calibrator(
        TemperatureCalibrator,
        procedure_file=procedure_file,
    )
    app.state.evolver.hardware["test"].read = lambda: [1.23, 2.34, 3.45]

    # Resume the procedure using the dedicated resume endpoint
    start_response = client.post("/hardware/test/calibrator/procedure/resume")
    assert start_response.status_code == 200

    # dispatch an action
    dispatch_response = dispatch_action(client, "test", "read_vial_0_raw_output")
    assert dispatch_response.status_code == 200

    # Save procedure state
    save_response = client.post("/hardware/test/calibrator/procedure/save")
    assert save_response.status_code == 200

    before_resume = save_response.json()

    # Create new client to simulate fresh start, this client will have the same procedure_file as the first client.
    # because the procedure attached to this client will be resumed from later, we want to make sure it has a procedure_file attirbute defined.
    _, new_client = setup_evolver_with_calibrator(TemperatureCalibrator, procedure_file=procedure_file)

    # Resume procedure using the resume endpoint
    resume_response = new_client.post("/hardware/test/calibrator/procedure/resume")
    assert resume_response.status_code == 200
    after_resume = resume_response.json()

    # assert resume state matches last saved state
    assert after_resume == before_resume


def test_calibration_procedure_undo_action_utility(tmp_path):
    _, client = setup_evolver_with_calibrator(TemperatureCalibrator)

    app.state.evolver.hardware["test"].read = lambda: [1.23, 2.34, 3.45]
    procedure_file = str(tmp_path / "my_test_calibration_procedure.yml")
    client.post(
        "/hardware/test/calibrator/procedure/start",
        params={"procedure_file": procedure_file},
    )

    dispatch_response = dispatch_action(client, "test", "read_vial_0_raw_output")
    assert dispatch_response.status_code == 200

    undo_response = client.post("/hardware/test/calibrator/procedure/undo")
    assert undo_response.status_code == 200

    expected_subset = get_empty_calibration_state()
    assert expected_subset.items() <= undo_response.json().items()


def test_calibration_procedure_save(tmp_path):
    _, client = setup_evolver_with_calibrator(TemperatureCalibrator)
    app.state.evolver.hardware["test"].read = lambda: [1.23, 2.34, 3.45]

    procedure_file = str(tmp_path / "my_test_calibration_procedure.yml")
    # Start procedure with the new start endpoint
    client.post(
        "/hardware/test/calibrator/procedure/start",
        params={
            "procedure_file": procedure_file,
        },
    )

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
    temp_calibrator, client = setup_evolver_with_calibrator(TemperatureCalibrator)

    procedure_file = str(tmp_path / "my_test_calibration_procedure.yml")
    app.state.evolver.hardware["test"].read = lambda: [1.23, 2.34, 3.45]

    client.post("/hardware/test/calibrator/procedure/start", params={"resume": False, "procedure_file": procedure_file})

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
    }

    assert actual_state == expected_state


def test_calibration_procedure_apply(tmp_path):
    # Setup fs for save and two files.
    procedure_file = str(tmp_path / "my_test_calibration_procedure.yml")
    calibration_file = str(tmp_path / "calibration_file.yml")

    # Initialize with only procedure_file
    temp_calibrator, client = setup_evolver_with_calibrator(TemperatureCalibrator)
    app.state.evolver.hardware["test"].read = lambda: [1.23, 2.34, 3.45]

    # Start procedure with the new start endpoint
    client.post("/hardware/test/calibrator/procedure/start", params={"procedure_file": procedure_file})

    # Collect calibration procedure data
    dispatch_action(client, "test", "measure_vial_0_temperature", {"temperature": 25.0})
    dispatch_action(client, "test", "read_vial_0_raw_output")
    dispatch_action(client, "test", "calculate_vial_0_fit")

    # Save the procedure first to ensure procedure_file is created and contains state from the procedure
    save_response = client.post("/hardware/test/calibrator/procedure/save")
    assert save_response.status_code == 200

    # Test successful apply with explicit calibration_file
    apply_response = client.post(
        "/hardware/test/calibrator/procedure/apply", params={"calibration_file": calibration_file}
    )
    assert apply_response.status_code == 200

    # Verify that the calibration_file was updated and procedure_file was cleared
    assert temp_calibrator.calibration_file == calibration_file
    assert temp_calibrator.procedure_file is None

    # Verify the correct state was set on the calibrator
    assert "0" in temp_calibrator.calibration_data.measured or 0 in temp_calibrator.calibration_data.measured
    measured_data = temp_calibrator.calibration_data.measured.get("0", temp_calibrator.calibration_data.measured.get(0))
    assert measured_data["raw"] == [1.23]
    assert measured_data["reference"] == [25.0]

    # Test apply with no calibrator, providing a dummy calibration file path
    no_calibrator_response = client.post(
        "/hardware/test/calibrator/procedure/apply", params={"calibration_file": calibration_file}
    )
    assert no_calibrator_response.status_code == 500

    # Test apply with no procedure started
    app.state.evolver.hardware["test"].calibrator.calibration_procedure = None
    no_procedure_response = client.post(
        f"/hardware/test/calibrator/procedure/apply?calibration_file={calibration_file}"
    )
    assert no_procedure_response.json() == {"started": False}

    # Test apply failure with missing procedure_file
    app.state.evolver.hardware["test"].calibrator.calibration_procedure = MagicMock()
    app.state.evolver.hardware["test"].calibrator.calibration_procedure.apply.side_effect = ValueError(
        "procedure_file attribute is not set"
    )
    error_response = client.post(
        "/hardware/test/calibrator/procedure/apply", params={"calibration_file": calibration_file}
    )
    assert error_response.status_code == 500

    # Test apply with general exception
    app.state.evolver.hardware["test"].calibrator.calibration_procedure.apply.side_effect = Exception
    error_response = client.post(
        "/hardware/test/calibrator/procedure/apply", params={"calibration_file": calibration_file}
    )
    assert error_response.status_code == 500
