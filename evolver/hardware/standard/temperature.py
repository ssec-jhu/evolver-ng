from copy import copy

from pydantic import Field
from pydantic.fields import FieldInfo

from evolver.base import ConfigDescriptor
from evolver.calibration.interface import Calibrator
from evolver.hardware.interface import (
    EffectorDriver,
    HardwareDriver,
    SensorDriver,
)
from evolver.hardware.standard.base import SerialDeviceConfigBase, SerialDeviceOutputBase
from evolver.serial import SerialData
from evolver.settings import settings


class Temperature(SensorDriver, EffectorDriver):
    """Temperature sensor and heater package.

    Goes over the evolver serial protocol and is capable of both reading the current
    temperature value as well as setting a target for heating. A particular raw value
    stands in for off (HEAT_OFF property of this class).
    """

    HEAT_OFF = b"4095"

    class Config(SerialDeviceConfigBase, EffectorDriver.Config):
        calibrator: ConfigDescriptor | Calibrator | None = FieldInfo.merge_field_infos(
            HardwareDriver.Config.model_fields["calibrator"],
            default_factory=lambda: ConfigDescriptor.load(settings.DEFAULT_TEMPERATURE_CALIBRATION_CONFIG_FILE),
        )

    class Output(SerialDeviceOutputBase, SensorDriver.Output):
        temperature: float | None = Field(None, description="Sensor temperature in degrees Celsius")

    class Input(EffectorDriver.Input):
        temperature: float = Field(description="Target temperature in degrees Celsius")

    @property
    def serial(self):
        return self.serial_conn or self.evolver.serial

    def _do_serial(self, from_proposal=False):
        data = [self.HEAT_OFF] * self.slots
        # since a read is also a send, we load all committed values as a base and
        # in the case of proposals overwrite with new data.
        inputs = copy(self.committed)
        if from_proposal:
            inputs.update({k: v for k, v in self.proposal.items() if k in self.vials})
        for vial, input in inputs.items():
            # Calibrate temperature to raw data.
            raw = int(self._transform("input_transformer", "convert_from", input.temperature, vial))
            data[vial] = str(raw).encode()
        with self.serial as comm:
            response = comm.communicate(SerialData(addr=self.addr, data=data))
        self.committed = inputs
        return response

    def read(self):
        self.outputs.clear()
        response = self._do_serial()
        for vial, raw in enumerate(response.data):
            if vial in self.vials:
                # Calibrate raw data to temperature.
                raw = int(raw)
                temperature = self._transform("output_transformer", "convert_to", raw, vial)
                # Temperature can be None if transformation fails or isn't configured correctly
                # This is handled gracefully since Output model allows temperature to be None
                self.outputs[vial] = self.Output(vial=vial, raw=raw, temperature=temperature)
        return self.outputs

    def commit(self):
        self._do_serial(from_proposal=True)

    def off(self):
        cmd = [self.HEAT_OFF] * self.slots
        with self.serial as comm:
            comm.communicate(SerialData(addr=self.addr, data=cmd))
