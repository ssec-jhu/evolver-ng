from evolver.controller.interface import Controller


class NoOpController(Controller):
    ncalls = 0

    def react(self):
        self.ncalls += 1
