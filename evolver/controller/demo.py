from evolver.controller.interface import Controller


class NoOpController(Controller):
    ncalls = 0

    def control(self, *args, **kwargs):
        self.ncalls += 1
