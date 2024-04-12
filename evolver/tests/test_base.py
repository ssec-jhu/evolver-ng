import evolver.base


class ConcreteInterface(evolver.base.BaseInterface):
    class Config(evolver.base.BaseConfig):
        a: int = 2
        b: int = 3

    def __init__(self, a, b):
        super().__init__()
        self.a = a
        self.b = b


class TestBaseInterface:
    def test_create(self):
        obj = ConcreteInterface.create()
        assert obj.a == 2
        assert obj.b == 3

        obj = ConcreteInterface.create(ConcreteInterface.Config(a=6, b=7))
        assert obj.a == 6
        assert obj.b == 7

    def test_config_stash(self):
        assert ConcreteInterface(4, 5)._config is None
        assert ConcreteInterface.create()._config == ConcreteInterface.Config()

        config = ConcreteInterface.Config(a=6, b=7)
        assert ConcreteInterface.create(config)._config == config
