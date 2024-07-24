from copy import copy

from pydantic import Field

from evolver.hardware.interface import EffectorDriver
from evolver.hardware.standard.base import SerialDeviceConfigBase
from evolver.serial import SerialData


class LED(EffectorDriver):
    class Config(SerialDeviceConfigBase, EffectorDriver.Config):
        pwm_max: int = 4095
        default_brightness: float = 1.0

    class Input(EffectorDriver.Input):
        brightness: float = Field(1.0, ge=0, le=1, description="brightness on scale of 0 to 1")

    @property
    def serial(self):
        return self.serial_conn or self.evolver.serial

    def commit(self):
        inputs = copy(self.committed)
        inputs.update({v: i for v, i in self.proposal.items() if v in self.vials})

        def from_brightness(brightness):
            # no calibration needed, the brightness range just comes from time-on via
            # PWM duty cycle
            return str(min(self.pwm_max, max(0, int(self.pwm_max * brightness)))).encode()

        cmd = [from_brightness(self.default_brightness)] * self.slots
        for v, i in inputs.items():
            cmd[v] = from_brightness(i.brightness)
        with self.serial as comm:
            comm.communicate(SerialData(addr=self.addr, data=cmd))
        self.committed = inputs
