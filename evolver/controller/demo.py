from evolver.controller.interface import Controller
from evolver.logutils import EVENT


class NoOpController(Controller):
    ncalls = 0

    def control(self, *args, **kwargs):
        self.logger.log(EVENT, "NoOpController control called")
        self.ncalls += 1
