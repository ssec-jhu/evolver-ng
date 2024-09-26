from copy import copy
from typing import Any

from pydantic import Field

from evolver.base import BaseConfig, ConfigDescriptor
from evolver.calibration.interface import Calibrator, IndependentVialBasedCalibrator, Transformer
from evolver.calibration.standard.polyfit import LinearTransformer
from evolver.hardware.interface import EffectorDriver
from evolver.hardware.standard.base import SerialDeviceConfigBase
from evolver.serial import SerialData


class GenericPumpCalibrator(IndependentVialBasedCalibrator):
    class Config(IndependentVialBasedCalibrator.Config):
        time_to_pump_fast: float = 10.0
        time_to_pump_slow: float = 100.0
        calibration_file: str = None
        use_cached_fit: bool = True

    class CalibrationData(Transformer.Config):
        time_to_pump: float
        measured: dict[int, tuple[list[float], list[float]]] = {}
        fit: dict[int, ConfigDescriptor] = {}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.time_to_pump = self.time_to_pump_fast
        self.input_transformer = self.input_transformer or {}
        if self.calibration_file is not None:
            self.load_calibration()

    def load_calibration(self, calibration_data: CalibrationData | None = None):
        if calibration_data is not None:
            self.cal_data = calibration_data
        elif self.calibration_file is not None:
            self.cal_data = self.CalibrationData.load(self.dir / self.calibration_file)
        else:
            raise ValueError("no calibration file or data provided")

        self.time_to_pump = self.cal_data.time_to_pump
        if self.use_cached_fit and self.cal_data.fit:
            for vial, fit in self.cal_data.fit.items():
                self.input_transformer[vial] = fit.create()
        else:
            for vial, (raw, measured) in self.cal_data.measured.items():
                self.input_transformer[vial] = LinearTransformer.create(LinearTransformer.fit(raw, measured))

    def run_calibration_procedure(self, *args, **kwargs):
        pass


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
        calibrator: ConfigDescriptor | Calibrator = GenericPumpCalibrator()

    class Input(BaseConfig):  # This intentionally doesn't inherit from EffectorDriver.Input.
        pump_id: int
        flow_rate: float

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.ipp_pumps is True:
            self.ipp_pumps = list(range(self.slots / 3))
        elif self.ipp_pumps in (False, None):
            self.ipp_pumps = []

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
                # The calibration is done at a particular speed, represented by
                # time_to_pump and should only be valid for that speed.
                time_to_pump = self.calibrator.time_to_pump
                pump_interval = int(self._transform("input_transformer", "convert_from", input.flow_rate, pump))
                cmd[pump] = f"{time_to_pump}|{pump_interval}".encode()
        with self.serial as comm:
            comm.communicate(SerialData(addr=self.addr, data=cmd))
        self.committed = inputs


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
        calibrator: ConfigDescriptor | Calibrator = VialIEPumpCalibrator()

        def model_post_init(self, *args, **kwargs) -> None:
            super().model_post_init(*args, **kwargs)
            self.influx_map = self.influx_map or {i: i for i in range(0, self.slots * 3)}
            self.efflux_map = self.efflux_map or {i: i + self.slots for i in range(0, self.slots * 3)}

    class Input(EffectorDriver.Input):
        flow_rate: float = Field(None, description="influx/efflux flow rate in ml/s")
        flow_rate_influx: float = Field(None, description="influx flow rate in ml/s")
        flow_rate_efflux: float = Field(None, description="efflux flow rate in ml/s")

        def model_post_init(self, __context: Any) -> None:
            super().model_post_init(__context)
            if self.flow_rate is not None:
                if self.flow_rate_influx is not None or self.flow_rate_efflux is not None:
                    raise ValueError("cannot specify both flow_rate and flow_rate_influx/efflux")
                self.flow_rate_influx = self.flow_rate_efflux = self.flow_rate
            elif self.flow_rate_influx is None or self.flow_rate_efflux is None:
                raise ValueError("must specify either flow_rate or both flow_rate_influx/efflux")

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
                self._generic_pump.set(GenericPump.Input(pump_id=self.influx_map[p.vial], flow_rate=p.flow_rate_influx))
                self._generic_pump.set(GenericPump.Input(pump_id=self.efflux_map[p.vial], flow_rate=p.flow_rate_efflux))
        self._generic_pump.commit()
        self.committed = copy(self.proposal)
