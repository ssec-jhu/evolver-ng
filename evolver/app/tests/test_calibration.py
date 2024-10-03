from evolver.calibration.interface import TemperatureCalibrator
from evolver.tests.conftest import tmp_calibration_dir  # noqa: F401

from evolver.app.main import app
from evolver.device import Evolver
from evolver.calibration.demo import NoOpCalibrator
from evolver.hardware.demo import NoOpSensorDriver


from fastapi.testclient import TestClient


class TestCalibration:
    def test_get_calibration_status(self):
        # Set up the evolver instance with hardware and a calibrator
        evolver_instance = Evolver(
            hardware={
                "temp": NoOpSensorDriver(
                    name="temp",
                    calibrator=NoOpCalibrator(state={"status": "calibrated"}),  # Mock calibrator state
                    vials=[0, 1, 2],  # Simulate 3 vials
                ),
                "ph": NoOpSensorDriver(
                    name="ph",
                    calibrator=NoOpCalibrator(state={"status": "not calibrated"}),
                    vials=[0, 1, 2],
                ),
            }
        )
        # Set the evolver state in the app before testing
        app.state.evolver = evolver_instance

        # Create the test client
        client = TestClient(app)

        # Test the "temp" hardware's calibrator state
        response = client.get("/hardware/temp/calibrator/state")
        assert response.status_code == 200

        # Check the returned state
        temp_calibrator_state = response.json()
        assert temp_calibrator_state["status"] == "calibrated"
        response = client.get("/hardware/ph/calibrator/state")
        assert response.status_code == 200
        ph_calibrator_state = response.json()
        assert ph_calibrator_state["status"] == "not calibrated"

    def test_start_temperature_calibration_procedure(self):
        # Set up the evolver instance with hardware and a Temperature Calibrator
        temp_calibrator = TemperatureCalibrator()  # Ensure this is properly initialized

        # Create NoOpSensorDriver and assign the temp calibrator to it
        evolver_instance = Evolver(
            hardware={"temp": NoOpSensorDriver(name="temp", calibrator=temp_calibrator, vials=[0, 1, 2])}
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

        # Test the "temp" hardware's calibrator state
        response = client.post("/hardware/temp/calibrator/start", json=request_payload)
        assert response.status_code == 200

        # Check the returned state
        temp_calibrator_state = response.json()
        assert request_payload["selected_vials"] == temp_calibrator_state["selected_vials"]

        # Check the state persists on the hardware.
        # get the "temp" hardware's calibrator state after it has been started.
        state_response = client.get("/hardware/temp/calibrator/state")
        assert state_response.status_code == 200
        # Check the returned state
        temp_calibrator_state_2 = state_response.json()
        assert request_payload["selected_vials"] == temp_calibrator_state_2["selected_vials"]


def test_temperature_calibration_procedure_actions():
    # Set up the evolver instance with hardware and a Temperature Calibrator
    temp_calibrator = TemperatureCalibrator()  # Ensure this is properly initialized

    # Create NoOpSensorDriver and assign the temp calibrator to it
    evolver_instance = Evolver(
        hardware={"temp": NoOpSensorDriver(name="temp", calibrator=temp_calibrator, vials=[0, 1, 2])}
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
    response = client.post("/hardware/temp/calibrator/start", json=request_payload)
    assert response.status_code == 200

    # Verify the available actions in the calibration procedure
    actions_response = client.post("hardware/temp/calibrator/actions")
    assert actions_response.status_code == 200
    expected_actions = [
        {"name": action.name, "description": action.description}
        for action in temp_calibrator.calibration_procedure.actions
    ]

    # Check if the actions returned by the endpoint match the expected actions
    actual_actions = actions_response.json()["actions"]
    print("EXPECTED ACTIONS:", expected_actions)
    print("ACTUAL ACTIONS:", actual_actions)
    assert len(actual_actions) == len(expected_actions)

    # Verify that each expected action is present
    for expected_action in expected_actions:
        assert expected_action in actual_actions


def test_dispatch_temperature_calibration_action():
    # Set up the evolver instance with hardware and a Temperature Calibrator
    temp_calibrator = TemperatureCalibrator()  # Ensure this is properly initialized

    # Create NoOpSensorDriver and assign the temp calibrator to it
    evolver_instance = Evolver(
        hardware={"temp": NoOpSensorDriver(name="temp", calibrator=temp_calibrator, vials=[0, 1, 2])}
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
    response = client.post("/hardware/temp/calibrator/start", json=request_payload)
    assert response.status_code == 200

    # Now we will dispatch an action to the calibrator
    action_payload = {"action_name": "Vial_0_Temp_Reference_Value_Action", "payload": {"reference_value": 25.0}}

    # Dispatch the action
    dispatch_response = client.post("/hardware/temp/calibrator/dispatch", json=action_payload)
    assert dispatch_response.status_code == 200
    assert dispatch_response.json() == {"state": {"temp": {"vial_0": {"reference": [25.0], "raw": []}}}}
