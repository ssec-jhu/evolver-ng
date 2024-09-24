from evolver.tests.conftest import tmp_calibration_dir  # noqa: F401

from evolver.app.main import app
from evolver.device import Evolver
from evolver.calibration.demo import NoOpCalibrator
from evolver.hardware.demo import NoOpSensorDriver


from fastapi.testclient import TestClient

# Import your main FastAPI app


class TestApp:
    def test_get_all_hardware(self):
        # Set up the evolver instance in app state before running the test
        app.state.evolver = Evolver(
            hardware={
                "temp": NoOpSensorDriver(calibrator=NoOpCalibrator()),
                "ph": NoOpSensorDriver(calibrator=NoOpCalibrator()),
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
