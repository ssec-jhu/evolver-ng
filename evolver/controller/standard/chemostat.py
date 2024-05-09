import time
from pydantic import Field
from collections import defaultdict, deque
from evolver.controller.interface import Controller
from evolver.hardware.interface import VialConfigBaseModel


class Chemostat(Controller):
    class Config(VialConfigBaseModel):
        od_sensor: str = Field(description="name of OD sensor to use")
        pump: str = Field(description="name of pump device to use")
        stirrer: str = Field(description="name of stirrer device to use")
        window: int = Field(7, description="number of OD measurements to collect prior to start")
        min_od: float = Field(0, description="OD at which to start chemostat dilutions")
        start_delay: int = Field(0, description="Time (in hours) after which to start dilutions")
        flow_rate: float = Field(0, description="Flow rate for dilutions")
        stir_rate: float = Field(8, description="Stir rate")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # buffer could come from history as well
        self.od_buffer = defaultdict(lambda: deque(maxlen=self.config.window))
        # start_time is something we might actually want to be a property of
        # evolver, in case of interrupt it has a chance of continuing - but can
        # come from history similarly
        self.start_time = time.time()

    @property
    def od(self):
        return self.evolver.hardware.get(self.config.od_sensor)

    @property
    def pump(self):
        return self.evolver.hardware.get(self.config.pump)

    @property
    def stir(self):
        return self.evolver.hardware.get(self.config.stirrer)

    def control(self, *args, **kwargs):
        od_values = self.od.get()
        elapsed_time = time.time() - self.start_time

        if set(self.config.vials or []) - set(od_values):
            raise ValueError(f'missing vials: I want: {self.config.vials}, OD provides: {od_values.keys()}')

        for vial, od_value in od_values.items():
            if self.config.vials and vial not in self.config.vials:
                continue

            # Load the rotating window buffer with latest value and only proceed
            # with dilutions if both we have the full window loaded and it has
            # been configured time since start
            self.od_buffer[vial].append(od_value.density)
            if len(self.od_buffer[vial]) < self.config.window or elapsed_time < self.config.start_delay * 3600:
                continue

            od_mean = sum(self.od_buffer[vial]) / self.config.window
            if self.config.min_od > od_mean:
                continue

            # Inputs assume the relevant device has its calibration and takes
            # the target real value. These may be missing spec, for example does
            # pump need bolus value also?
            self.pump.set(self.pump.Input(vial=vial, flow_rate=self.config.flow_rate))
            self.stir.set(self.stir.Input(vial=vial, stir_rate=self.config.stir_rate))
