from evolver.tests.conftest import tmp_calibration_dir  # noqa: F401

from evolver.app.main import app
from evolver.device import Evolver
from evolver.calibration.demo import NoOpCalibrator
from evolver.hardware.demo import NoOpSensorDriver


from fastapi.testclient import TestClient

# Import your main FastAPI app


class TestHardware:
    def test_get_all_hardware(self):
        # Set up the evolver instance in app state before running the test
        app.state.evolver = Evolver(
            hardware={
                "temp": NoOpSensorDriver(
                    calibrator=NoOpCalibrator(),
                    vials=[0, 1, 2],  # Simulate 3 vials
                ),
                "ph": NoOpSensorDriver(
                    calibrator=NoOpCalibrator(),
                    vials=[0, 1, 2],  # Simulate 3 vials
                ),
            }
        )

        # Create the test client
        client = TestClient(app)

        # Make the request and check the response
        response = client.get("/hardware/")
        assert response.status_code == 200

        hardware = response.json()

        assert "temp" in hardware
        assert "ph" in hardware

    def test_get_hardware(self):
        # Setup the evolver instance with hardware
        app.state.evolver = Evolver(
            hardware={
                "temp": NoOpSensorDriver(
                    name="temp",
                    calibrator=NoOpCalibrator(),  # Pass in the NoOpCalibrator
                    vials=[0, 1, 2],  # Simulate 3 vials
                )
            }
        )

        # Call read to populate sensor data
        app.state.evolver.hardware["temp"].read()

        # Create the test client
        client = TestClient(app)
        response = client.get("/hardware/temp")
        assert response.status_code == 200

        # Get the hardware data from the response
        temp_hardware = response.json()

        # 1. Assert the length of the hardware matches the number of vials passed
        assert len(temp_hardware) == 3, f"Expected 3 vials, but got {len(temp_hardware)}"

        # 2. Assert that each vial has the correct "name", "raw", "value", and "vial"
        for vial_id, vial_data in temp_hardware.items():
            # Assert the vial ID is as expected
            assert vial_id in ["0", "1", "2"], f"Unexpected vial ID: {vial_id}"

            # Assert the 'name' field is correct
            assert vial_data["name"] == "temp", f"Expected name 'temp', but got {vial_data['name']}"

            # Assert the 'raw' value is as expected the NoOpSensorDriver defaults to 1
            assert vial_data["raw"] == 1, f"Expected raw value 1, but got {vial_data['raw']}"

            # Assert the 'value' is as expected the NoOpSensorDriver defaults to 2
            assert vial_data["value"] == 2, f"Expected value 2, but got {vial_data['value']}"

            # Assert the 'vial' field matches the vial ID
            assert vial_data["vial"] == int(vial_id), f"Expected vial {vial_id}, but got {vial_data['vial']}"

    def test_get_calibration_status(self):
        # Set up the evolver instance with hardware and a calibrator
        app.state.evolver = Evolver(
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
