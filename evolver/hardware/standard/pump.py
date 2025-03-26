from copy import copy

from pydantic import Field, model_validator

from evolver.base import BaseConfig, ConfigDescriptor
from evolver.calibration.interface import Calibrator
from evolver.calibration.standard.calibrators.pump import GenericPumpCalibrator
from evolver.hardware.interface import EffectorDriver
from evolver.hardware.standard.base import SerialDeviceConfigBase
from evolver.serial import SerialData


class GenericPump(EffectorDriver):
    """Pump control for evolver fluidics directly by pump ID.

    This driver controls either or both of standard and IPP pumps according to the
    arduino fluidics module. Pumps are indexed by pump ID (either position in array or
    IPP pump number) and not vial, each must be controlled separately.

    Specify the index of any IPP pumps via the config parameter ipp_pumps, this should
    be an array of those pump IDs that are IPP. Please note that IPP pumps reserve 3
    slots (1 for each solenoid), so if pump 0 is IPP, 1 and 2 cannot be assigned as
    non-IPP pumps.
    """

    class Config(SerialDeviceConfigBase, EffectorDriver.Config):
        ipp_pumps: bool | list[int] = Field(False, description="False (no IPP), True (all IPP), or list of IPP ids")
        calibrator: ConfigDescriptor | Calibrator = ConfigDescriptor(classinfo=GenericPumpCalibrator)
        active_pumps: list[int] | None = Field(None, description="List of active pump IDs, or None for all")

    class Input(BaseConfig):  # This intentionally doesn't inherit from EffectorDriver.Input.
        pump_id: int
        volume: float = Field(0, description="Volume to pump in mL per event")
        rate: float = Field(0, description="Rate of pumping in volumes per hour")
        time: float = Field(0, description="Time to pump in seconds, mutually exclusive with volume")

        @model_validator(mode="after")
        def validate(self):
            if self.volume and self.time:
                raise ValueError("Only one of volume or time can be specified")
            return self

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pump_ids = list(range(self.slots)) if self.active_pumps is None else self.active_pumps
        if self.ipp_pumps is True:
            self.ipp_pumps = list(range(self.slots / 3))
        elif self.ipp_pumps in (False, None):
            self.ipp_pumps = []

    @property
    def serial(self):
        return self.serial_conn or self.evolver.serial

    def set(self, *args, **kwargs):
        # We index here by pump_id, which is a concept outside of vial - we
        # don't want confuse things by overloading the concept, so be explicit
        # here
        input = self._get_input_from_args(*args, **kwargs)
        if input.pump_id not in self.pump_ids:
            raise ValueError(f"pump_id {input.pump_id} not in active pumps")
        self.proposal[input.pump_id] = input

    def commit(self):
        inputs = copy(self.committed)
        inputs.update(self.proposal.items())
        cmd = [b"--"] * self.slots
        for pump, input in inputs.items():
            if pump in self.ipp_pumps:
                # TODO: calibation transform here. The IPP pumps should return array of
                # hz values per solenoid number - containing 3 of them.
                hz_a = [float(input.volume)] * 3
                for solenoid, hz in enumerate(hz_a):
                    # solenoid is 1-indexed on hardware
                    cmd[pump * 3 + solenoid] = f"{hz}|{pump}|{solenoid + 1}"
            elif any(pump - i < 3 for i in self.ipp_pumps):
                raise ValueError(f"pump slot {pump} reserved for IPP pump, cannot address as standard")
            else:
                if input.time:
                    time_to_pump = input.time
                else:
                    time_to_pump = self._transform("input_transformer", "convert_from", input.volume, pump)
                pump_interval = int(3600 / input.rate) if input.rate else 0
                cmd[pump] = f"{time_to_pump}|{pump_interval}".encode()
        with self.serial as comm:
            comm.communicate(SerialData(addr=self.addr, data=cmd))
        self.committed = inputs

    def off(self):
        cmd = [b"0"] * self.slots
        for pump in self.ipp_pumps:
            for solenoid in range(3):
                cmd[pump * 3 + solenoid] = f"0|{pump}|{solenoid + 1}".encode()
        with self.serial as comm:
            comm.communicate(SerialData(addr=self.addr, data=cmd))


class VialIEPumpCalibrator(GenericPumpCalibrator):
    def run_calibration_procedure(self, *args, **kwargs):
        # This may or may not even be required, though we probably do need a way
        # to go from vials to pump ids in the procedure start. The generic pump
        # one will work on IDs
        pass


class VialIEPump(EffectorDriver):
    """Vial-based Influx-Efflux Pump driver.

    Each pump in the array is either an influx (to bring liquid to the vial) or
    efflux (to pull waste out of vial) or spare (unused). Flow rates can be configured
    separately or as a single rate.

    Configuration parameters ``influx_map`` and ``efflux_map`` can be used to specify
    explicit mapping between vial and underlying pump_id (of :py:class:`GenericPump`),
    which by default reserves the first 3rd of slots to influx, and second third to
    efflux (remaining are spare).
    """

    class Config(GenericPump.Config):
        influx_map: dict[int, int] | None = Field(None, description="map of vial to influx pump ID")
        efflux_map: dict[int, int] | None = Field(None, description="map of vial to efflux pump ID")
        calibrator: ConfigDescriptor | Calibrator = ConfigDescriptor(classinfo=VialIEPumpCalibrator)

        def model_post_init(self, *args, **kwargs) -> None:
            super().model_post_init(*args, **kwargs)
            self.influx_map = self.influx_map or {i: i for i in range(0, self.slots * 3)}
            self.efflux_map = self.efflux_map or {i: i + self.slots for i in range(0, self.slots * 3)}

    class Input(EffectorDriver.Input):
        efflux_volume: float = Field(description="Volume to pump out in mL per event")
        influx_volume: float = Field(description="Volume to pump in in mL per event")
        efflux_rate: float = Field(0, description="Rate of efflux in volumes per hour")
        influx_rate: float = Field(0, description="Rate of influx in volumes per hour")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._generic_pump = GenericPump(
            addr=self.addr,
            slots=self.slots * 3,  # influx, efflux, spare (or 3 solenoids for IPP)
            serial=self.serial_conn,
            ipp_pumps=self.ipp_pumps,
            evolver=kwargs.get("evolver"),
            calibrator=self.calibrator,
        )

    def commit(self):
        for p in self.proposal.values():
            if p.vial in self.vials:
                self._generic_pump.set(
                    GenericPump.Input(pump_id=self.influx_map[p.vial], volume=p.influx_volume, rate=p.influx_rate)
                )
                self._generic_pump.set(
                    GenericPump.Input(pump_id=self.efflux_map[p.vial], volume=p.efflux_volume, rate=p.efflux_rate)
                )
        self._generic_pump.commit()
        self.committed = copy(self.proposal)

    def off(self):
        self._generic_pump.off()
