from pydantic import Field

from evolver.controller.interface import Controller
from evolver.logutils import EVENT


class NoOpController(Controller):
    class Config(Controller.Config):
        vial_volume: float = Field(20.0, description="Volume of vial in mL")
        start_delay: int = Field(1, description="Time (in hours) after which to start")
        min_od: float = Field(0.5, description="Minimum OD threshold")
        bolus_volume: float = Field(2.0, description="Volume of bolus in mL")
        dilution_rate: float = Field(0.1, description="In vial_volume per hour")
        stir_rate: float = Field(8, description="Stir rate")
    
    ncalls = 0

    def control(self, *args, **kwargs):
        self.logger.log(EVENT, "NoOpController control called")
        self.ncalls += 1
