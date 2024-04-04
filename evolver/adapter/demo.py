from evolver.adapter.interface import Adapter


class NoOpAdapter(Adapter):
    ncalls = 0

    def react(self):
        self.ncalls += 1
