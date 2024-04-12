import pytest

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

    def test_json_config(self):
        obj = ConcreteInterface.create(ConcreteInterface.Config(a=4, b=5).model_dump_json())
        assert obj.a == 4
        assert obj.b == 5


class TestConfigDescriptor:
    @pytest.fixture()
    def mock_descriptor(self):
        return evolver.base.ConfigDescriptor(classinfo="evolver.tests.test_base.ConcreteInterface",
                                             config=dict(a=11, b=22))

    def test_create(self, mock_descriptor):
        obj = mock_descriptor.create()
        assert obj.a == 11
        assert obj.b == 22
