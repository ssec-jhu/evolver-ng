from copy import copy

from pydantic import Field

from evolver.base import BaseConfig
from evolver.hardware.interface import EffectorDriver, VialBaseModel
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

    class Config(SerialDeviceConfigBase):
        ipp_pumps: list[int] = Field([], description="Indexes of IPP mode pumps, per solenoid")

    class Input(BaseConfig):
        pump_id: int
        flow_rate: float

    @property
    def serial(self):
        return self.serial_conn or self.evolver.serial

    def set(self, input):
        self.proposal[input.pump_id] = input

    def commit(self):
        inputs = copy(self.committed)
        inputs.update(self.proposal.items())
        cmd = [b"--"] * self.slots
        for pump, input in inputs.items():
            if pump in self.ipp_pumps:
                # TODO: calibation transform here. The IPP pumps should return array of
                # hz values per solenoid number - containing 3 of them.
                hz_a = [input.flow_rate] * 3
                for solenoid, hz in enumerate(hz_a):
                    # solenoid is 1-indexed on hardware
                    cmd[pump * 3 + solenoid] = f"{hz}|{pump}|{solenoid+1}"
            elif any(pump - i < 3 for i in self.ipp_pumps):
                raise ValueError(f"pump slot {pump} reserved for IPP pump, cannot address as standard")
            else:
                # TODO: calibration transform here. The time_to_pump is the target variable
                # where pump_interval would presumably be what the pump_interval was set to
                # during calibration and is fixed post-calibration.
                time_to_pump, pump_interval = (input.flow_rate, int(input.flow_rate))
                cmd[pump] = f"{time_to_pump}|{pump_interval}".encode()
        with self.serial as comm:
            comm.communicate(SerialData(addr=self.addr, data=cmd))
        self.committed = inputs


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

    class Input(VialBaseModel):
        flow_rate_influx: float = Field(description="influx flow rate in ml/s")
        flow_rate_efflux: float | None = Field(None, description="efflux flow rate in ml/s. Defaults to same as influx")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        p_slots = self.slots * 3  # influx, efflux, spare (or 3 solenoids for IPP)
        self._generic_pump = GenericPump(
            addr=self.addr,
            slots=p_slots,
            serial=self.serial_conn,
            ipp_pumps=self.ipp_pumps,
            evolver=kwargs.get("evolver"),
        )
        self.influx_map = self.influx_map or {i: i for i in range(0, p_slots)}
        self.efflux_map = self.efflux_map or {i: i + self.slots for i in range(0, p_slots)}

    def commit(self):
        for p in self.proposal.values():
            if p.vial in self.vials:
                if p.flow_rate_efflux is None:
                    p.flow_rate_efflux = p.flow_rate_influx
                self._generic_pump.set(GenericPump.Input(pump_id=self.influx_map[p.vial], flow_rate=p.flow_rate_influx))
                self._generic_pump.set(GenericPump.Input(pump_id=self.efflux_map[p.vial], flow_rate=p.flow_rate_efflux))
        self._generic_pump.commit()
        self.committed = copy(self.proposal)
