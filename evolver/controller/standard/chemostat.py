import time
from collections import defaultdict, deque

from pydantic import Field

from evolver.controller.interface import Controller
from evolver.hardware.interface import HardwareDriver, VialConfigBaseModel


class Chemostat(Controller):
    class Config(Controller.Config, VialConfigBaseModel):
        od_sensor: HardwareDriver | str = Field(description="name of OD sensor to use")
        pump: HardwareDriver | str = Field(description="name of pump device to use")
        stirrer: HardwareDriver | str = Field(description="name of stirrer device to use")
        window: int = Field(7, description="number of OD measurements to collect prior to start")
        min_od: float = Field(0, description="OD at which to start chemostat dilutions")
        start_delay: int = Field(0, description="Time (in hours) after which to start dilutions")
        dilution_rate: float = Field(0, description="In vial_volume per hour")
        bolus_volume: float = Field(1, description="Volume of bolus in mL")
        vial_volume: float = Field(1, description="Volume of vial in mL")
        stir_rate: float = Field(8, description="Stir rate")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # buffer could come from history as well
        self.od_buffer = defaultdict(lambda: deque(maxlen=self.window))

        # start_time is something we might actually want to be a property of
        # evolver, in case of interrupt it has a chance of continuing - but can
        # come from history similarly
        self.start_time = time.time()

    def control(self, *args, **kwargs):
        od_values = self.get_hw(self.od_sensor).get()
        elapsed_time = time.time() - self.start_time

        if set(self.vials) - set(od_values):
            raise ValueError(f"missing vials: I want: {self.vials}, OD provides: {od_values.keys()}")

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
            # the target real value.
            self.get_hw(self.pump).set(
                vial=vial,
                influx_volume=self.bolus_volume,
                influx_rate=self.dilution_rate * self.vial_volume / self.bolus_volume,  # rate relative to vial vol
                efflux_volume=self.bolus_volume,
                efflux_rate=self.dilution_rate * self.vial_volume / self.bolus_volume,
            )
            self.get_hw(self.stirrer).set(vial=vial, stir_rate=self.stir_rate)
