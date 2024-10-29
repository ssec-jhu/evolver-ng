from fastapi.testclient import TestClient

from evolver.app.main import app
from evolver.calibration.demo import NoOpCalibrator
from evolver.calibration.standard.calibrators.temperature import TemperatureCalibrator
from evolver.calibration.standard.polyfit import LinearTransformer
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

        response = client.post(
            "/hardware/test/calibrator/procedure/start",
        )
        assert response.status_code == 200
        response = client.get("/hardware/test/calibrator/procedure/state")
        assert response.status_code == 200
        assert response.json() == {}


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

    # Test the "temp" hardware's calibrator initialization
    response = client.post("/hardware/test/calibrator/procedure/start")
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


def test_dispatch_temperature_calibration_bad_reference_value_action():
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

    # Test the "temp" hardware's calibrator initialization
    response = client.post(
        "/hardware/test/calibrator/procedure/start",
    )
    assert response.status_code == 200

    # Now we will dispatch an action to the calibrator
    action_payload = {"action_name": "measure_vial_0_temperature", "payload": {"this_should_not_work": 25.0}}

    # Dispatch the action
    dispatch_response = client.post("/hardware/test/calibrator/procedure/dispatch", json=action_payload)
    assert dispatch_response.status_code == 422


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

    # Test the "temp" hardware's calibrator initialization
    response = client.post("/hardware/test/calibrator/procedure/start")
    assert response.status_code == 200

    # Now we will dispatch an action to the calibrator
    action_payload = {"action_name": "read_vial_0_raw_output"}

    # Dispatch the action
    dispatch_response = client.post("/hardware/test/calibrator/procedure/dispatch", json=action_payload)
    assert dispatch_response.status_code == 200
    assert dispatch_response.json() == {"0": {"reference": [], "raw": [1.23]}}


def test_dispatch_temperature_calibration_calculate_fit_action():
    # Set up the evolver instance with hardware and a Temperature Calibrator
    temp_calibrator = TemperatureCalibrator(
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

    # Test the "temp" hardware's calibrator initialization
    response = client.post("/hardware/test/calibrator/procedure/start")
    assert response.status_code == 200

    # Dispatch the action to set the reference value
    reference_action_payload = {"action_name": "measure_vial_0_temperature", "payload": {"temperature": 25.0}}
    reference_dispatch_response = client.post(
        "/hardware/test/calibrator/procedure/dispatch", json=reference_action_payload
    )
    assert reference_dispatch_response.status_code == 200
    assert reference_dispatch_response.json() == {"0": {"reference": [25.0], "raw": []}}

    # Dispatch the action to read the raw value
    raw_action_payload = {"action_name": "read_vial_0_raw_output", "payload": {}}
    raw_dispatch_response = client.post("/hardware/test/calibrator/procedure/dispatch", json=raw_action_payload)
    assert raw_dispatch_response.status_code == 200
    assert raw_dispatch_response.json() == {"0": {"reference": [25.0], "raw": [1.23]}}

    # Dispatch the action to calculate the fit
    fit_action_payload = {"action_name": "calculate_vial_0_fit"}
    fit_dispatch_response = client.post("/hardware/test/calibrator/procedure/dispatch", json=fit_action_payload)
    assert fit_dispatch_response.status_code == 200
    assert fit_dispatch_response.json() == {"0": {"reference": [25.0], "raw": [1.23]}}

    output_transformer_response = client.get("/hardware/test/calibrator/output_transformer")
    assert output_transformer_response.status_code == 200
    assert output_transformer_response.json()["0"]["parameters"] == [0.6149999999999997, 0.024599999999999997]


def test_get_calibration_data():
    # Set up the evolver instance with hardware and a Temperature Calibrator
    temp_calibrator = TemperatureCalibrator(
        input_transformer={
            0: LinearTransformer(),
            1: LinearTransformer(),
            2: LinearTransformer(),
        },
        output_transformer={
            0: LinearTransformer(),
            1: LinearTransformer(),
            2: LinearTransformer(),
        },
    )

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
    calibration_data_response = client.post("/hardware/test/calibrator/procedure/start")
    assert calibration_data_response.status_code == 200

    # Dispatch actions to set reference value, read raw value, and calculate fit
    reference_dispatch_response = client.post(
        "/hardware/test/calibrator/procedure/dispatch",
        json={"action_name": "measure_vial_0_temperature", "payload": {"temperature": 25.0}},
    )
    assert reference_dispatch_response.status_code == 200
    assert reference_dispatch_response.json()["0"]["reference"] == [25.0]

    raw_dispatch_response = client.post(
        "/hardware/test/calibrator/procedure/dispatch", json={"action_name": "read_vial_0_raw_output", "payload": {}}
    )
    assert raw_dispatch_response.status_code == 200
    assert raw_dispatch_response.json()["0"]["raw"] == [1.23]

    fit_dispatch_response = client.post(
        "/hardware/test/calibrator/procedure/dispatch", json={"action_name": "calculate_vial_0_fit"}
    )
    assert fit_dispatch_response.status_code == 200
    # Save the calibration procedure state
    save_dispatch_response = client.post(
        "/hardware/test/calibrator/procedure/dispatch",
        json={"action_name": "save_calibration_procedure_state", "payload": {}},
    )
    assert save_dispatch_response.status_code == 200
    calibration_data_response = client.get("/hardware/test/calibrator/data")
    assert calibration_data_response.status_code == 200
    calibration_data = calibration_data_response.json()

    assert calibration_data["measured"] == {
        "0": {
            "raw": [1.23],
            "reference": [25.0],
        }
    }
