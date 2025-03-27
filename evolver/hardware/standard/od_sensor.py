from pydantic import Field
from pydantic.fields import FieldInfo

from evolver.base import ConfigDescriptor
from evolver.calibration.interface import Calibrator
from evolver.hardware.interface import SensorDriver
from evolver.hardware.standard.base import SerialDeviceConfigBase, SerialDeviceOutputBase
from evolver.serial import SerialData
from evolver.settings import settings


class ODSensor(SensorDriver):
    """Optical density sensor driver

    This driver represents a family of sensors for turbidity which are read by
    integrating a specified number of ADC readings per vial.
    """

    class Config(SerialDeviceConfigBase, SensorDriver.Config):
        integrations: int = Field(500, description="on read, request average of this number of ADC reads")

    class Output(SerialDeviceOutputBase, SensorDriver.Output):
        density: float | None = Field(None, description="Optical density")

    @property
    def serial(self):
        return self.serial_conn or self.evolver.serial

    def read(self):
        self.outputs.clear()
        cmd = SerialData(addr=self.addr, data=[str(self.integrations).encode()], kind="r")
        with self.serial as comm:
            response = comm.communicate(cmd)
        for vial, raw in enumerate(response.data):
            if vial in self.vials:
                # Calibrate raw data to density.
                raw = int(raw)
                density = self._transform("output_transformer", "convert_to", raw, vial)
                self.outputs[vial] = self.Output(vial=vial, raw=raw, density=density)
        return self.outputs


class OD90(ODSensor):
    class Config(ODSensor.Config):
        name: str = FieldInfo.merge_field_infos(
            ODSensor.Config.model_fields["name"],
            default="od_90",
        )
        addr: str = FieldInfo.merge_field_infos(
            ODSensor.Config.model_fields["addr"],
            default="od_90",
        )
        calibrator: ConfigDescriptor | Calibrator | None = FieldInfo.merge_field_infos(
            ODSensor.Config.model_fields["calibrator"],
            default_factory=lambda: ConfigDescriptor.load(settings.DEFAULT_OD90_CALIBRATION_CONFIG_FILE),
        )


class OD135(ODSensor):
    class Config(ODSensor.Config):
        name: str = FieldInfo.merge_field_infos(
            ODSensor.Config.model_fields["name"],
            default="od_135",
        )
        addr: str = FieldInfo.merge_field_infos(
            ODSensor.Config.model_fields["addr"],
            default="od_135",
        )
        calibrator: ConfigDescriptor | Calibrator | None = FieldInfo.merge_field_infos(
            ODSensor.Config.model_fields["calibrator"],
            default_factory=lambda: ConfigDescriptor.load(settings.DEFAULT_OD135_CALIBRATION_CONFIG_FILE),
        )
