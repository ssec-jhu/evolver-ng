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
                "temp": NoOpSensorDriver(
                    name="temp",
                    calibrator=NoOpCalibrator(),  # Mock calibrator state
                    vials=[0, 1, 2],  # Simulate 3 vials
                ),
                "ph": NoOpSensorDriver(
                    name="ph",
                    calibrator=NoOpCalibrator(),
                    vials=[0, 1, 2],
                ),
            }
        )
        # Set the evolver state in the app before testing
        app.state.evolver = evolver_instance

        # Create the test client
        client = TestClient(app)
        # Prepare the request payload to initialize the calibration procedure
        request_payload = {
            "selected_vials": [0, 1, 2],  # Simulate the user selecting vials for calibration
        }

        # Test the "temp" hardware's calibrator state
        response = client.post("/hardware/temp/calibrator/procedure/start", json=request_payload)
        assert response.status_code == 200

        # Test the "temp" hardware's calibrator state
        response = client.get("/hardware/temp/calibrator/procedure/state")
        assert response.status_code == 200
        assert response.json() == {"selected_vials": [0, 1, 2]}


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
    response = client.post("/hardware/temp/calibrator/procedure/start", json=request_payload)
    assert response.status_code == 200

    # Verify the available actions in the calibration procedure
    actions_response = client.get("hardware/temp/calibrator/procedure/actions")
    print(actions_response.json())
    assert actions_response.status_code == 200
    expected_actions = [
        {"name": action.name, "description": action.description}
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
    response = client.post("/hardware/temp/calibrator/procedure/start", json=request_payload)
    assert response.status_code == 200

    # Now we will dispatch an action to the calibrator
    action_payload = {"action_name": "Vial_0_Temp_Reference_Value_Action", "payload": {"temperature": 25.0}}

    # Dispatch the action
    dispatch_response = client.post("/hardware/temp/calibrator/procedure/dispatch", json=action_payload)
    assert dispatch_response.status_code == 200
    assert dispatch_response.json() == {
        "state": {"selected_vials": [0, 1, 2], "temp": {"vial_0": {"reference": [25.0], "raw": []}}}
    }


def test_dispatch_temperature_calibration_raw_value_action():
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

    # Mock the hardware read method to return a meaningful value
    evolver_instance.hardware["temp"].read = lambda: [1.23, 2.34, 3.45]

    # Create the test client
    client = TestClient(app)

    # Prepare the request payload to initialize the calibration procedure
    request_payload = {
        "selected_vials": [0, 1, 2]  # Simulate the user selecting vials for calibration
    }

    # Test the "temp" hardware's calibrator initialization
    response = client.post("/hardware/temp/calibrator/procedure/start", json=request_payload)
    assert response.status_code == 200

    # Now we will dispatch an action to the calibrator
    action_payload = {"action_name": "Vial_0_Temp_Raw_Voltage_Action", "payload": {}}

    # Dispatch the action
    dispatch_response = client.post("/hardware/temp/calibrator/procedure/dispatch", json=action_payload)
    assert dispatch_response.status_code == 200
    assert dispatch_response.json() == {
        "state": {"selected_vials": [0, 1, 2], "temp": {"vial_0": {"reference": [], "raw": [1.23]}}}
    }


def test_dispatch_temperature_calibration_calculate_fit_action():
    # Set up the evolver instance with hardware and a Temperature Calibrator
    temp_calibrator = TemperatureCalibrator()

    # Create NoOpSensorDriver and assign the temp calibrator to it
    evolver_instance = Evolver(
        hardware={"temp": NoOpSensorDriver(name="temp", calibrator=temp_calibrator, vials=[0, 1, 2])}
    )

    # Ensure the temp calibrator has access to the evolver
    temp_calibrator.evolver = evolver_instance

    # Set the evolver state in the app before testing
    app.state.evolver = evolver_instance

    # Mock the hardware read method to return a meaningful value
    evolver_instance.hardware["temp"].read = lambda: [1.23, 2.34, 3.45]

    # Create the test client
    client = TestClient(app)

    # Prepare the request payload to initialize the calibration procedure
    request_payload = {
        "selected_vials": [0, 1, 2]  # Simulate the user selecting vials for calibration
    }

    # Test the "temp" hardware's calibrator initialization
    response = client.post("/hardware/temp/calibrator/procedure/start", json=request_payload)
    assert response.status_code == 200

    # Dispatch the action to set the reference value
    reference_action_payload = {"action_name": "Vial_0_Temp_Reference_Value_Action", "payload": {"temperature": 25.0}}
    reference_dispatch_response = client.post(
        "/hardware/temp/calibrator/procedure/dispatch", json=reference_action_payload
    )
    assert reference_dispatch_response.status_code == 200
    assert reference_dispatch_response.json() == {
        "state": {"selected_vials": [0, 1, 2], "temp": {"vial_0": {"reference": [25.0], "raw": []}}}
    }

    # Dispatch the action to read the raw value
    raw_action_payload = {"action_name": "Vial_0_Temp_Raw_Voltage_Action", "payload": {}}
    raw_dispatch_response = client.post("/hardware/temp/calibrator/procedure/dispatch", json=raw_action_payload)
    assert raw_dispatch_response.status_code == 200
    assert raw_dispatch_response.json() == {
        "state": {"selected_vials": [0, 1, 2], "temp": {"vial_0": {"reference": [25.0], "raw": [1.23]}}}
    }

    # Dispatch the action to calculate the fit
    fit_action_payload = {"action_name": "Vial_0_Temp_Calculate_Fit_Action", "payload": {}}
    fit_dispatch_response = client.post("/hardware/temp/calibrator/procedure/dispatch", json=fit_action_payload)
    assert fit_dispatch_response.status_code == 200
    fit_dispatch_response_json = fit_dispatch_response.json()
    vial_0_data = fit_dispatch_response_json["state"]["temp"]["vial_0"]

    assert vial_0_data["reference"] == [25.0]
    assert vial_0_data["raw"] == [1.23]

    output_fit_parameters = vial_0_data["output_fit_parameters"]

    assert "name" in output_fit_parameters
    assert "dir" in output_fit_parameters
    assert "created" in output_fit_parameters
    assert "expire" in output_fit_parameters
    assert output_fit_parameters["degree"] == 1
    assert output_fit_parameters["parameters"] == [0.6149999999999997, 0.024599999999999997]


def test_get_calibration_data():
    # Set up the evolver instance with hardware and a Temperature Calibrator
    temp_calibrator = TemperatureCalibrator()

    # Create NoOpSensorDriver and assign the temp calibrator to it
    evolver_instance = Evolver(
        hardware={"temp": NoOpSensorDriver(name="temp", calibrator=temp_calibrator, vials=[0, 1, 2])}
    )

    # Ensure the temp calibrator has access to the evolver
    temp_calibrator.evolver = evolver_instance

    # Set the evolver state in the app before testing
    app.state.evolver = evolver_instance

    # Mock the hardware read method to return a meaningful value
    evolver_instance.hardware["temp"].read = lambda: [1.23, 2.34, 3.45]

    # Create the test client
    client = TestClient(app)

    # Prepare the request payload to initialize the calibration procedure
    request_payload = {
        "selected_vials": [0, 1, 2]  # Simulate the user selecting vials for calibration
    }

    # Test the "temp" hardware's calibrator initialization
    calibration_data_response = client.post("/hardware/temp/calibrator/procedure/start", json=request_payload)
    assert calibration_data_response.status_code == 200

    # Dispatch the action to set the reference value
    reference_action_payload = {"action_name": "Vial_0_Temp_Reference_Value_Action", "payload": {"temperature": 25.0}}
    reference_dispatch_response = client.post(
        "/hardware/temp/calibrator/procedure/dispatch", json=reference_action_payload
    )
    assert reference_dispatch_response.status_code == 200
    assert reference_dispatch_response.json() == {
        "state": {"selected_vials": [0, 1, 2], "temp": {"vial_0": {"reference": [25.0], "raw": []}}}
    }

    # Dispatch the action to read the raw value
    raw_action_payload = {"action_name": "Vial_0_Temp_Raw_Voltage_Action", "payload": {}}
    raw_dispatch_response = client.post("/hardware/temp/calibrator/procedure/dispatch", json=raw_action_payload)
    assert raw_dispatch_response.status_code == 200
    assert raw_dispatch_response.json() == {
        "state": {"selected_vials": [0, 1, 2], "temp": {"vial_0": {"reference": [25.0], "raw": [1.23]}}}
    }

    # Dispatch the action to calculate the fit
    fit_action_payload = {"action_name": "Vial_0_Temp_Calculate_Fit_Action"}
    fit_dispatch_response = client.post("/hardware/temp/calibrator/procedure/dispatch", json=fit_action_payload)
    assert fit_dispatch_response.status_code == 200

    save_action_payload = {"action_name": "Save_Calibration_Procedure_State_Action", "payload": {}}

    save_dispatch_response = client.post("/hardware/temp/calibrator/procedure/dispatch", json=save_action_payload)
    assert save_dispatch_response.status_code == 200

    # Assert that the calibration data contains state from the now complete calibration_procedure
    calibration_data_response = client.get("/hardware/temp/calibrator/data")
    assert calibration_data_response.status_code == 200
    calibration_data = calibration_data_response.json()
    assert "dir" in calibration_data
    assert "created" in calibration_data
    assert "expire" in calibration_data
    assert "calibration_procedure_state" in calibration_data
    assert "temp" in calibration_data["calibration_procedure_state"]
    assert "vial_0" in calibration_data["calibration_procedure_state"]["temp"]
    vial_0_data = calibration_data["calibration_procedure_state"]["temp"]["vial_0"]
    assert vial_0_data["reference"] == [25.0]
    assert vial_0_data["raw"] == [1.23]
