from fastapi.testclient import TestClient

from evolver.app.main import app
from evolver.calibration.demo import NoOpCalibrator
from evolver.calibration.standard.calibrators.temperature import TemperatureCalibrator
from evolver.device import Evolver
from evolver.hardware.demo import NoOpSensorDriver
from evolver.tests.conftest import tmp_calibration_dir  # noqa: F401


class TestCalibration:
    def test_get_calibration_status(self):
        # Set up the evolver instance with hardware and a calibrator
        evolver_instance = Evolver(
            hardware={
                "test": NoOpSensorDriver(
                    name="test",
                    calibrator=NoOpCalibrator(),
                    vials=[0, 1, 2],
                ),
                "ph": NoOpSensorDriver(
                    name="ph",
                    calibrator=NoOpCalibrator(),
                    vials=[0, 1, 2],
                ),
            }
        )
        app.state.evolver = evolver_instance
        client = TestClient(app)
        initial_state = {
            "selected_vials": [
                0,
                1,
                2,
            ],
        }
        response = client.post("/hardware/test/calibrator/procedure/start", json=initial_state)
        assert response.status_code == 200
        response = client.get("/hardware/test/calibrator/procedure/state")
        assert response.status_code == 200
        assert response.json() == {"selected_vials": [0, 1, 2]}


def test_temperature_calibration_procedure_actions():
    # Set up the evolver instance with hardware and a Temperature Calibrator
    temp_calibrator = TemperatureCalibrator()  # Ensure this is properly initialized

    # Create NoOpSensorDriver and assign the temp calibrator to it
    evolver_instance = Evolver(
        hardware={"test": NoOpSensorDriver(name="test", calibrator=temp_calibrator, vials=[0, 1, 2])}
    )

    # Ensure the temp calibrator has access to the evolver
    temp_calibrator.evolver = evolver_instance

    # Set the evolver state in the app before testing
    app.state.evolver = evolver_instance

    # Create the test client
    client = TestClient(app)

    # Prepare the request payload to initialize the calibration procedure
    request_payload = {
        "selected_vials": [0, 1, 2]  # Simulate the user selecting vials for calibration
    }

    # Test the "temp" hardware's calibrator initialization
    response = client.post("/hardware/test/calibrator/procedure/start", json=request_payload)
    assert response.status_code == 200

    # Verify the available actions in the calibration procedure
    actions_response = client.get("hardware/test/calibrator/procedure/actions")
    assert actions_response.status_code == 200
    expected_actions = [
        {"name": action.model.name, "description": action.model.description}
        for action in temp_calibrator.calibration_procedure.actions
    ]

    # Check if the actions returned by the endpoint match the expected actions
    actual_actions = actions_response.json()["actions"]
    assert len(actual_actions) == len(expected_actions)

    # Verify that each expected action is present
    for expected_action in expected_actions:
        assert expected_action in actual_actions


def test_dispatch_temperature_calibration_reference_value_action():
    # Set up the evolver instance with hardware and a Temperature Calibrator
    temp_calibrator = TemperatureCalibrator()  # Ensure this is properly initialized

    # Create NoOpSensorDriver and assign the temp calibrator to it
    evolver_instance = Evolver(
        hardware={"test": NoOpSensorDriver(name="test", calibrator=temp_calibrator, vials=[0, 1, 2])}
    )

    # Ensure the temp calibrator has access to the evolver
    temp_calibrator.evolver = evolver_instance

    # Set the evolver state in the app before testing
    app.state.evolver = evolver_instance

    # Create the test client
    client = TestClient(app)

    # Prepare the request payload to initialize the calibration procedure
    request_payload = {
        "selected_vials": [0, 1, 2]  # Simulate the user selecting vials for calibration
    }

    # Test the "temp" hardware's calibrator initialization
    response = client.post("/hardware/test/calibrator/procedure/start", json=request_payload)
    assert response.status_code == 200

    # Now we will dispatch an action to the calibrator
    action_payload = {"action_name": "Vial_0_Temp_Reference_Value_Action", "payload": {"temperature": 25.0}}

    # Dispatch the action
    dispatch_response = client.post("/hardware/test/calibrator/procedure/dispatch", json=action_payload)
    assert dispatch_response.status_code == 200
    assert dispatch_response.json() == {
        "state": {
            "selected_vials": [0, 1, 2],
            "vial_data": {"0": {"fit": {}, "reference": [25.0], "raw": []}},
        }
    }


def test_dispatch_temperature_calibration_raw_value_action():
    # Set up the evolver instance with hardware and a Temperature Calibrator
    temp_calibrator = TemperatureCalibrator()  # Ensure this is properly initialized

    # Create NoOpSensorDriver and assign the temp calibrator to it
    evolver_instance = Evolver(
        hardware={"test": NoOpSensorDriver(name="test", calibrator=temp_calibrator, vials=[0, 1, 2])}
    )

    # Ensure the temp calibrator has access to the evolver
    temp_calibrator.evolver = evolver_instance

    # Set the evolver state in the app before testing
    app.state.evolver = evolver_instance

    # Mock the hardware read method to return a meaningful value
    evolver_instance.hardware["test"].read = lambda: [1.23, 2.34, 3.45]

    # Create the test client
    client = TestClient(app)

    # Prepare the request payload to initialize the calibration procedure
    request_payload = {
        "selected_vials": [0, 1, 2]  # Simulate the user selecting vials for calibration
    }

    # Test the "temp" hardware's calibrator initialization
    response = client.post("/hardware/test/calibrator/procedure/start", json=request_payload)
    assert response.status_code == 200

    # Now we will dispatch an action to the calibrator
    action_payload = {"action_name": "Vial_0_Temp_Raw_Voltage_Action", "payload": {}}

    # Dispatch the action
    dispatch_response = client.post("/hardware/test/calibrator/procedure/dispatch", json=action_payload)
    assert dispatch_response.status_code == 200
    assert dispatch_response.json() == {
        "state": {
            "selected_vials": [0, 1, 2],
            "vial_data": {"0": {"fit": {}, "reference": [], "raw": [1.23]}},
        }
    }


def test_dispatch_temperature_calibration_calculate_fit_action():
    # Set up the evolver instance with hardware and a Temperature Calibrator
    temp_calibrator = TemperatureCalibrator()

    # Create NoOpSensorDriver and assign the temp calibrator to it
    evolver_instance = Evolver(
        hardware={"test": NoOpSensorDriver(name="test", calibrator=temp_calibrator, vials=[0, 1, 2])}
    )

    # Ensure the temp calibrator has access to the evolver
    temp_calibrator.evolver = evolver_instance

    # Set the evolver state in the app before testing
    app.state.evolver = evolver_instance

    # Mock the hardware read method to return a meaningful value
    evolver_instance.hardware["test"].read = lambda: [1.23, 2.34, 3.45]

    # Create the test client
    client = TestClient(app)

    # Prepare the request payload to initialize the calibration procedure
    request_payload = {
        "selected_vials": [0, 1, 2]  # Simulate the user selecting vials for calibration
    }

    # Test the "temp" hardware's calibrator initialization
    response = client.post("/hardware/test/calibrator/procedure/start", json=request_payload)
    assert response.status_code == 200

    # Dispatch the action to set the reference value
    reference_action_payload = {"action_name": "Vial_0_Temp_Reference_Value_Action", "payload": {"temperature": 25.0}}
    reference_dispatch_response = client.post(
        "/hardware/test/calibrator/procedure/dispatch", json=reference_action_payload
    )
    assert reference_dispatch_response.status_code == 200
    assert reference_dispatch_response.json() == {
        "state": {
            "selected_vials": [0, 1, 2],
            "vial_data": {"0": {"fit": {}, "reference": [25.0], "raw": []}},
        }
    }

    # Dispatch the action to read the raw value
    raw_action_payload = {"action_name": "Vial_0_Temp_Raw_Voltage_Action", "payload": {}}
    raw_dispatch_response = client.post("/hardware/test/calibrator/procedure/dispatch", json=raw_action_payload)
    assert raw_dispatch_response.status_code == 200
    assert raw_dispatch_response.json() == {
        "state": {
            "selected_vials": [0, 1, 2],
            "vial_data": {"0": {"fit": {}, "reference": [25.0], "raw": [1.23]}},
        }
    }

    # Dispatch the action to calculate the fit
    fit_action_payload = {"action_name": "Vial_0_Temp_Calculate_Fit_Action", "payload": {}}
    fit_dispatch_response = client.post("/hardware/test/calibrator/procedure/dispatch", json=fit_action_payload)
    assert fit_dispatch_response.status_code == 200
    fit_dispatch_response_json = fit_dispatch_response.json()
    vial_0_data = fit_dispatch_response_json["state"]["vial_data"]["0"]

    assert vial_0_data["reference"] == [25.0]
    assert vial_0_data["raw"] == [1.23]

    fit = vial_0_data["fit"]

    assert "name" in fit
    assert "dir" in fit
    assert "created" in fit
    assert "expire" in fit
    assert fit["degree"] == 1
    assert fit["parameters"] == [0.6149999999999997, 0.024599999999999997]


def test_get_calibration_data():
    # Set up the evolver instance with hardware and a Temperature Calibrator
    temp_calibrator = TemperatureCalibrator()

    # Create NoOpSensorDriver and assign the temp calibrator to it
    evolver_instance = Evolver(
        hardware={"test": NoOpSensorDriver(name="test", calibrator=temp_calibrator, vials=[0, 1, 2])}
    )
    temp_calibrator.evolver = evolver_instance
    app.state.evolver = evolver_instance

    # Mock the hardware read method
    evolver_instance.hardware["test"].read = lambda: [1.23, 2.34, 3.45]
    client = TestClient(app)

    # Initialize the calibration procedure
    calibration_data_response = client.post(
        "/hardware/test/calibrator/procedure/start", json={"selected_vials": [0, 1, 2]}
    )
    assert calibration_data_response.status_code == 200

    # Dispatch actions to set reference value, read raw value, and calculate fit
    reference_dispatch_response = client.post(
        "/hardware/test/calibrator/procedure/dispatch",
        json={"action_name": "Vial_0_Temp_Reference_Value_Action", "payload": {"temperature": 25.0}},
    )
    assert reference_dispatch_response.status_code == 200
    assert reference_dispatch_response.json()["state"]["vial_data"]["0"]["reference"] == [25.0]

    raw_dispatch_response = client.post(
        "/hardware/test/calibrator/procedure/dispatch",
        json={"action_name": "Vial_0_Temp_Raw_Voltage_Action", "payload": {}},
    )
    assert raw_dispatch_response.status_code == 200
    assert raw_dispatch_response.json()["state"]["vial_data"]["0"]["raw"] == [1.23]

    fit_dispatch_response = client.post(
        "/hardware/test/calibrator/procedure/dispatch", json={"action_name": "Vial_0_Temp_Calculate_Fit_Action"}
    )
    assert fit_dispatch_response.status_code == 200

    # Save the calibration procedure state
    save_dispatch_response = client.post(
        "/hardware/test/calibrator/procedure/dispatch",
        json={"action_name": "Save_Calibration_Procedure_State_Action", "payload": {}},
    )
    assert save_dispatch_response.status_code == 200

    # Verify the saved calibration data contains the procedure state
    calibration_data_response = client.get("/hardware/test/calibrator/data")
    assert calibration_data_response.status_code == 200
    calibration_data = calibration_data_response.json()

    # Assertions on the top-level calibration data fields
    assert set(calibration_data.keys()).issuperset({"dir", "created", "expire"})
    persisted_procedure_state = calibration_data["calibration_procedure_state"]
    assert persisted_procedure_state["vial_data"]["0"]["fit"]["parameters"] == [
        0.6149999999999997,
        0.024599999999999997,
    ]
