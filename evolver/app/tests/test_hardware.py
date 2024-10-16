import json

from fastapi.testclient import TestClient

from evolver.app.main import app
from evolver.calibration.demo import NoOpCalibrator
from evolver.device import Evolver
from evolver.hardware.demo import NoOpEffectorDriver, NoOpSensorDriver
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

    def test_hardware_set(self):
        app.state.evolver = Evolver(
            hardware={
                "effector": NoOpEffectorDriver(),
                "sensor": NoOpSensorDriver(),
            }
        )
        client = TestClient(app)
        response = client.post("/hardware/effector/set", json={"vial": 0, "data": 30})
        assert response.status_code == 200
        proposals = [{"vial": 0, "data": 30}, {"vial": 1, "data": 40}]
        response = client.post("/hardware/effector/set", json=proposals)
        assert response.status_code == 200
        response = client.post("/hardware/effector/set?commit=true", json=proposals)
        assert response.status_code == 200
        assert app.state.evolver.hardware["effector"].committed == {
            p["vial"]: NoOpEffectorDriver.Input.model_validate(p) for p in proposals
        }

        response = client.post("/hardware/effector/set", json={"missing_vial": 0})
        assert response.status_code == 422
        try:
            NoOpEffectorDriver.Input.model_validate({"missing_vial": 0})
        except Exception as exc:
            # The ValidationError data is not 1-to-1 with deserialized JSON due
            # to containing tuples, so load from json, iso exc.errors()
            exception_ = json.loads(exc.json())
        assert exception_ == response.json()

        response = client.post("/hardware/sensor/set", json={"vial": 0, "data": 30})
        assert response.status_code == 400

    def test_hardware_commit(self):
        app.state.evolver = Evolver(
            hardware={
                "effector": NoOpEffectorDriver(),
                "sensor": NoOpSensorDriver(),
            }
        )
        client = TestClient(app)
        expected = {0: NoOpEffectorDriver.Input(vial=0, data=30)}
        app.state.evolver.hardware["effector"].set(expected[0])
        response = client.post("/hardware/effector/commit")
        assert response.status_code == 200
        assert app.state.evolver.hardware["effector"].committed == expected

        response = client.post("/hardware/sensor/commit")
        assert response.status_code == 400
