import pydantic
import pytest

import evolver.base


class ConcreteInterface(evolver.base.BaseInterface):
    class Config(evolver.base.BaseConfig):
        name: str = "TestDevice"
        a: int = 2
        b: int = 3

    def __init__(self, a, b, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.a = a
        self.b = b


@pytest.fixture()
def mock_descriptor():
    return evolver.base.ConfigDescriptor(classinfo="evolver.tests.test_base.ConcreteInterface",
                                         config=dict(a=11, b=22))


class TestBaseInterface:
    def test_create(self):
        obj = ConcreteInterface.create()
        assert obj.a == 2
        assert obj.b == 3

        obj = ConcreteInterface.create(ConcreteInterface.Config(a=6, b=7))
        assert obj.a == 6
        assert obj.b == 7

    def test_config_stash(self):
        assert ConcreteInterface(4, 5, "TestDevice")._config is None
        assert ConcreteInterface.create()._config == ConcreteInterface.Config()

        config = ConcreteInterface.Config(name="TestDevice", a=6, b=7)
        assert ConcreteInterface.create(config)._config == config

    def test_json_config(self):
        obj = ConcreteInterface.create(ConcreteInterface.Config(a=4, b=5, name="TestDevice").model_dump_json())
        assert obj.a == 4
        assert obj.b == 5

    def test_from_config_descriptor(self, mock_descriptor):
        obj = ConcreteInterface.create(mock_descriptor)
        assert obj.a == 11
        assert obj.b == 22


class TestConfigDescriptor:
    def test_create(self, mock_descriptor):
        obj = mock_descriptor.create()
        assert obj.a == 11
        assert obj.b == 22

    def test_create_with_overrides(self, mock_descriptor):
        obj = mock_descriptor.create(a=101)
        assert obj.a == 101
        assert obj.b == 22


def test_require_all_fields():
    for field in ConcreteInterface.Config.model_fields.values():
        assert not field.is_required()

    ConcreteInterface.Config(a=1)

    @evolver.base.require_all_fields
    class ConfigWithoutDefaults(ConcreteInterface.Config):
        ...

    for field in ConfigWithoutDefaults.model_fields.values():
        assert field.is_required()

    with pytest.raises(pydantic.ValidationError, match="Field required"):
        ConfigWithoutDefaults(a=1)
