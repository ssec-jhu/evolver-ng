from evolver.calibration.standard.calibrators.temperature import TemperatureCalibrator
from evolver.device import Evolver
from evolver.hardware.standard.temperature import Temperature

# calibrator=None
calibrator = TemperatureCalibrator()
x = Evolver(hardware={"test": Temperature(addr="x", calibrator=calibrator)}).config_model
print(x)
