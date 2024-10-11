from fastapi.testclient import TestClient

from evolver.app.main import app
from evolver.calibration.demo import NoOpCalibrator
from evolver.device import Evolver
from evolver.hardware.demo import NoOpSensorDriver
from evolver.tests.conftest import tmp_calibration_dir  # noqa: F401


class TestHardware:
    def test_get_all_hardware(self):
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

        client = TestClient(app)

        response = client.get("/hardware/")
        assert response.status_code == 200

        hardware = response.json()

        assert "temp" in hardware
        assert "ph" in hardware

    def test_get_hardware(self):
        app.state.evolver = Evolver(
            hardware={
                "temp": NoOpSensorDriver(
                    name="temp",
                    calibrator=NoOpCalibrator(),  # Pass in the NoOpCalibrator
                    vials=[0, 1, 2],  # Simulate 3 vials
                )
            }
        )

        app.state.evolver.hardware["temp"].read()

        client = TestClient(app)
        response = client.get("/hardware/temp")
        assert response.status_code == 200

        temp_hardware = response.json()

        assert len(temp_hardware) == 3, f"Expected 3 vials, but got {len(temp_hardware)}"

        for vial_id, vial_data in temp_hardware.items():
            assert vial_id in ["0", "1", "2"], f"Unexpected vial ID: {vial_id}"
            assert vial_data["name"] == "temp", f"Expected name 'temp', but got {vial_data['name']}"
            assert vial_data["raw"] == 1, f"Expected raw value 1, but got {vial_data['raw']}"
            assert vial_data["value"] == 2, f"Expected value 2, but got {vial_data['value']}"
            assert vial_data["vial"] == int(vial_id), f"Expected vial {vial_id}, but got {vial_data['vial']}"
