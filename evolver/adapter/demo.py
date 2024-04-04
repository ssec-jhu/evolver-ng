from evolver.adapter.interface import Adapter, VialAdapter


class NoOpAdapter(Adapter):
    ncalls = 0

    def react(self):
        self.ncalls += 1


class NoOpVialAdapter(VialAdapter):
    ncalls = 0

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.called_vials = set()

    def react_vial(self, vial):
        self.ncalls += 1
        self.called_vials.add(vial)
