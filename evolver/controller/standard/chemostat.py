import time
from collections import defaultdict, deque

from pydantic import Field

from evolver.base import ConfigDescriptor
from evolver.controller.interface import Controller
from evolver.hardware.interface import HardwareDriver, VialConfigBaseModel


class Chemostat(Controller):
    class Config(Controller.Config, VialConfigBaseModel):
        od_sensor: HardwareDriver | ConfigDescriptor | str = Field(description="name of OD sensor to use")
        pump: HardwareDriver | ConfigDescriptor | str = Field(description="name of pump device to use")
        stirrer: HardwareDriver | ConfigDescriptor | str = Field(description="name of stirrer device to use")
        window: int = Field(7, description="number of OD measurements to collect prior to start")
        min_od: float = Field(0, description="OD at which to start chemostat dilutions")
        start_delay: int = Field(0, description="Time (in hours) after which to start dilutions")
        dilution_rate: float = Field(0, description="In vial_volume per hour")
        bolus_volume: float = Field(1, description="Volume of bolus in mL")
        vial_volume: float = Field(1, description="Volume of vial in mL")
        stir_rate: float = Field(8, description="Stir rate")

    def __init__(
        self,
        *args,
        od_sensor: HardwareDriver | ConfigDescriptor | str,
        pump: HardwareDriver | ConfigDescriptor | str,
        stirrer: HardwareDriver | ConfigDescriptor | str,
        **kwargs,
    ):
        self._od_sensor = od_sensor
        self._pump = pump
        self._stirrer = stirrer

        # Since ``od_sensor`` and alike are properties that we explicitly initialize above, don't auto assign them
        # in ``BaseInterface.__init__`` from the ``Config``.
        super().__init__(*args, auto_config_ignore_fields=("od_sensor", "pump", "stirrer"), **kwargs)

        # buffer could come from history as well
        self.od_buffer = defaultdict(lambda: deque(maxlen=self.window))

        # start_time is something we might actually want to be a property of
        # evolver, in case of interrupt it has a chance of continuing - but can
        # come from history similarly
        self.start_time = time.time()

    @property
    def od_sensor(self):
        return self.evolver.hardware.get(self._od_sensor) if isinstance(self._od_sensor, str) else self._od_sensor

    @property
    def pump(self):
        return self.evolver.hardware.get(self._pump) if isinstance(self._pump, str) else self._pump

    @property
    def stirrer(self):
        return self.evolver.hardware.get(self._stirrer) if isinstance(self._stirrer, str) else self._stirrer

    def control(self, *args, **kwargs):
        od_values = self.od_sensor.get()
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
            self.pump.set(
                self.pump.Input(
                    vial=vial,
                    influx_volume=self.bolus_volume,
                    influx_rate=self.dilution_rate * self.vial_volume / self.bolus_volume,  # rate relative to vial vol
                    efflux_volume=self.bolus_volume,
                    efflux_rate=self.dilution_rate * self.vial_volume / self.bolus_volume,
                )
            )
            self.stirrer.set(self.stirrer.Input(vial=vial, stir_rate=self.stir_rate))
