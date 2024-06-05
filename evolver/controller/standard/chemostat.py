from collections import defaultdict, deque
import time

from pydantic import Field

from evolver.base import ConfigDescriptor
from evolver.controller.interface import Controller
from evolver.hardware.interface import VialConfigBaseModel, HardwareDriver


class Chemostat(Controller):
    class Config(VialConfigBaseModel):
        od_sensor: HardwareDriver | ConfigDescriptor | str = Field(description="name of OD sensor to use")
        pump: HardwareDriver | ConfigDescriptor | str = Field(description="name of pump device to use")
        stirrer: HardwareDriver | ConfigDescriptor | str = Field(description="name of stirrer device to use")
        window: int = Field(7, description="number of OD measurements to collect prior to start")
        min_od: float = Field(0, description="OD at which to start chemostat dilutions")
        start_delay: int = Field(0, description="Time (in hours) after which to start dilutions")
        flow_rate: float = Field(0, description="Flow rate for dilutions")
        stir_rate: float = Field(8, description="Stir rate")

    def __init__(self, *args, **kwargs):
        self._od_sensor = None
        self._pump = None
        self._stirrer = None

        super().__init__(*args, **kwargs)

        # buffer could come from history as well
        self.od_buffer = defaultdict(lambda: deque(maxlen=self.window))

        # start_time is something we might actually want to be a property of
        # evolver, in case of interrupt it has a chance of continuing - but can
        # come from history similarly
        self.start_time = time.time()

    @property
    def od_sensor(self):
        return self.evolver.hardware.get(self._od_sensor) if isinstance(self._od_sensor, str) else self._od_sensor

    @od_sensor.setter
    def od_sensor(self, value):
        if self._od_sensor is None:
            self._od_sensor = value
        else:
            raise AttributeError()

    @property
    def pump(self):
        return self.evolver.hardware.get(self._pump) if isinstance(self._pump, str) else self._pump

    @pump.setter
    def pump(self, value):
        if self._pump is None:
            self._pump = value
        else:
            raise AttributeError()

    @property
    def stirrer(self):
        return self.evolver.hardware.get(self._stirrer) if isinstance(self._stirrer, str) else self._stirrer

    @stirrer.setter
    def stirrer(self, value):
        if self._stirrer is None:
            self._stirrer = value
        else:
            raise AttributeError()

    def control(self, *args, **kwargs):
        od_values = self.od_sensor.get()
        elapsed_time = time.time() - self.start_time

        if set(self.vials) - set(od_values):
            raise ValueError(f'missing vials: I want: {self.vials}, OD provides: {od_values.keys()}')

        for vial, od_value in od_values.items():
            if self.vials and vial not in self.vials:
                continue

            # Load the rotating window buffer with latest value and only proceed
            # with dilutions if both we have the full window loaded and it has
            # been configured time since start
            self.od_buffer[vial].append(od_value.density)
            if len(self.od_buffer[vial]) < self.window or elapsed_time < self.start_delay * 3600:
                continue

            od_mean = sum(self.od_buffer[vial]) / self.window
            if self.min_od > od_mean:
                continue

            # Inputs assume the relevant device has its calibration and takes
            # the target real value. These may be missing spec, for example does
            # pump need bolus value also?
            self.pump.set(self.pump.Input(vial=vial, flow_rate=self.flow_rate))
            self.stirrer.set(self.stirrer.Input(vial=vial, stir_rate=self.stir_rate))
