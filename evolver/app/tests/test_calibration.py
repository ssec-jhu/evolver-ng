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
