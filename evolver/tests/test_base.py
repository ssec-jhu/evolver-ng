import json

import pydantic
import pytest

import evolver.base
import evolver.util
from evolver.calibration.standard.calibrators.temperature import TemperatureCalibrator
from evolver.device import Evolver
from evolver.hardware.standard.temperature import Temperature


class ConcreteInterface(evolver.base.BaseInterface):
    class Config(evolver.base.BaseInterface.Config):
        name: str = "TestDevice"
        a: int = 2
        b: int = 3


class ConcreteInterface2(evolver.base.BaseInterface): ...


class Nested(evolver.base.BaseInterface):
    class Config(evolver.base.BaseInterface.Config):
        stuff: evolver.base.ConfigDescriptor


@pytest.fixture()
def mock_descriptor():
    return evolver.base.ConfigDescriptor(classinfo="evolver.tests.test_base.ConcreteInterface", config=dict(a=11, b=22))


@pytest.fixture()
def mock_descriptor_as_dict(mock_descriptor):
    return mock_descriptor.model_dump()


@pytest.fixture()
def mock_descriptor_as_json(mock_descriptor):
    return mock_descriptor.model_dump_json()


@pytest.fixture()
def mock_conf_as_dict(mock_descriptor):
    return mock_descriptor.config


@pytest.fixture()
def mock_conf_as_json(mock_conf_as_dict):
    return json.dumps(mock_conf_as_dict)


@pytest.fixture()
def mock_config_file(tmp_path):
    file_path = tmp_path / "ConcreteInterfaceConfig.yml"
    ConcreteInterface.Config(a=44, b=55).save(file_path)
    return file_path


class TestBaseConfig:
    def test_empty_model_validate(self):
        obj = ConcreteInterface.Config.model_validate(None)
        assert isinstance(obj, ConcreteInterface.Config)

    def test_auto_json_handling(self):
        config = ConcreteInterface.Config(a=6, b=7)
        assert config.a == 6
        assert config.b == 7
        config = config.model_dump_json()
        obj = ConcreteInterface.Config.model_validate(config)
        assert isinstance(obj, ConcreteInterface.Config)
        assert obj.a == 6
        assert obj.b == 7

    @pytest.mark.parametrize("descriptor", ("mock_descriptor", "mock_descriptor_as_json"))
    def test_from_config_descriptor(self, descriptor, request):
        obj = ConcreteInterface.Config.model_validate(request.getfixturevalue(descriptor))
        assert isinstance(obj, ConcreteInterface.Config)
        assert obj.a == 11
        assert obj.b == 22

    def test_from_base_interface(self):
        obj = ConcreteInterface.Config.model_validate(ConcreteInterface(a=8, b=9))
        assert isinstance(obj, ConcreteInterface.Config)
        assert obj.a == 8
        assert obj.b == 9

    def test_from_file(self, mock_config_file):
        obj = ConcreteInterface.Config.model_validate(mock_config_file)
        assert obj.a == 44
        assert obj.b == 55

    def test_classinfo(self):
        assert ConcreteInterface.Config.get_classinfo() == evolver.util.fully_qualified_name(ConcreteInterface)


class TestBaseInterface:
    def test_create(self):
        obj = ConcreteInterface.create()
        assert obj.a == 2
        assert obj.b == 3

        obj = ConcreteInterface.create(ConcreteInterface.Config(a=6, b=7))
        assert obj.a == 6
        assert obj.b == 7

    def test_config_property(self):
        config = ConcreteInterface.Config(a=6, b=7)
        obj = ConcreteInterface.create(config)
        assert obj.config == config.dict()
        assert obj.Config.model_validate(config) == config

    @pytest.mark.parametrize("conf", ("mock_conf_as_json", "mock_conf_as_dict"))
    def test_from_conf(self, conf, request):
        obj = ConcreteInterface.create(request.getfixturevalue(conf))
        assert obj.a == 11
        assert obj.b == 22

    def test_descriptor_property(self):
        obj = ConcreteInterface.create()
        descriptor = obj.descriptor
        assert isinstance(descriptor, evolver.base.ConfigDescriptor)
        assert descriptor.classinfo is ConcreteInterface
        assert descriptor.config == obj.config

    def test_to_config_descriptor(self):
        obj = ConcreteInterface.create()
        descriptor = evolver.base.ConfigDescriptor.model_validate(obj)
        assert isinstance(descriptor, evolver.base.ConfigDescriptor)
        assert descriptor.classinfo is ConcreteInterface
        assert descriptor.config == obj.config

    @pytest.mark.parametrize("descriptor", ("mock_descriptor", "mock_descriptor_as_dict", "mock_descriptor_as_json"))
    def test_from_descriptor(self, descriptor, request):
        descriptor = request.getfixturevalue(descriptor)
        obj = ConcreteInterface.create(descriptor)
        assert obj.a == 11
        assert obj.b == 22

    def test_config_symmetry(self):
        assert ConcreteInterface.create().config == ConcreteInterface.Config().model_dump()
        assert ConcreteInterface.Config.model_validate(ConcreteInterface.create().config) == ConcreteInterface.Config()

    def test_config_as_json(self):
        obj = ConcreteInterface.create()
        assert obj.config_json == ConcreteInterface.Config().model_dump_json()

    def test_config_as_model(self):
        obj = ConcreteInterface.create()
        assert obj.config_model == ConcreteInterface.Config()

    def test_create_descriptor_cls_missmatch(self):
        config = ConcreteInterface.Config().model_dump()

        with pytest.raises(TypeError, match="is not compatible with this class"):
            ConcreteInterface.create(dict(classinfo=int, config=config))

    def test_create_descriptor_cls_missmatch_from_json(self):
        descriptor = evolver.base.ConfigDescriptor(classinfo=ConcreteInterface2, config={})
        with pytest.raises(TypeError, match="is not compatible with this class"):
            ConcreteInterface.create(descriptor.model_dump_json())

    def test_schema(self):
        class Foo(pydantic.BaseModel):
            interface: ConcreteInterface

        assert Foo.model_json_schema() == {
            "$defs": {
                "Config": {
                    "properties": {
                        "name": {"default": "TestDevice", "title": "Name", "type": "string"},
                        "a": {"default": 2, "title": "A", "type": "integer"},
                        "b": {"default": 3, "title": "B", "type": "integer"},
                    },
                    "title": "Config",
                    "type": "object",
                }
            },
            "properties": {"interface": {"$ref": "#/$defs/Config"}},
            "required": ["interface"],
            "title": "Foo",
            "type": "object",
        }

        obj = Foo(interface=ConcreteInterface.Config())
        assert obj.interface.a == 2
        assert obj.interface.b == 3
        assert obj.model_dump() == {"interface": {"name": "TestDevice", "a": 2, "b": 3}}

    def test_auto_config(self):
        obj = ConcreteInterface()
        assert obj.a == 2
        assert obj.b == 3

        obj = ConcreteInterface(a=4, b=5)
        assert obj.a == 4
        assert obj.b == 5

    def test_auto_config_off(self):
        obj = ConcreteInterface(auto_config=False)
        assert not hasattr(obj, "a")
        assert not hasattr(obj, "b")

    def test_auto_config_required_field_exception(self):
        class MyClass(ConcreteInterface):
            class Config(ConcreteInterface.Config):
                c: str

        with pytest.raises(KeyError, match="required but was missing upon instantiation"):
            MyClass()

    def test_auto_config_with_init_params(self):
        class MyClass(ConcreteInterface):
            class Config(ConcreteInterface.Config):
                c: str = "yo!"

            def __init__(self, *args, a=10, b=11, c="yep", **kwargs):
                self.a = a
                self.b = b
                self._c = c
                super().__init__(*args, auto_config_ignore_fields=("c",), *kwargs)

        obj = MyClass()
        assert obj.a == 10
        assert obj.b == 11
        assert obj._c == "yep"
        assert not hasattr(obj, "c")

    def test_from_file(self, mock_config_file):
        obj = ConcreteInterface.create(mock_config_file)
        assert obj.a == 44
        assert obj.b == 55

    def test_nested_config_models(self):
        # Setup.
        calibrator = TemperatureCalibrator()
        hardware = Temperature(addr="x", calibrator=calibrator)
        config = Evolver(hardware={"test": hardware}).config

        # Test hardware description.
        hardware_descriptor = config["hardware"]["test"]
        assert set(hardware_descriptor.keys()) == {"classinfo", "config"}
        assert hardware_descriptor["classinfo"] == evolver.util.fully_qualified_name(hardware.__class__)

        # Test calibrator description.
        calibrator_descriptor = hardware_descriptor["config"]["calibrator"]
        assert set(calibrator_descriptor.keys()) == {"classinfo", "config"}
        assert calibrator_descriptor["classinfo"] == evolver.util.fully_qualified_name(calibrator.__class__)


class TestConfigDescriptor:
    def test_create(self, mock_descriptor):
        obj = mock_descriptor.create()
        assert obj.a == 11
        assert obj.b == 22

    def test_create_with_empty_config(self):
        obj = evolver.base.ConfigDescriptor(classinfo="evolver.tests.test_base.ConcreteInterface").create()
        assert obj.a == 2
        assert obj.b == 3

    @pytest.mark.parametrize("kwargs", (dict(a=101), dict(update=dict(a=101)), dict(update=dict(a=102), a=101)))
    def test_create_with_overrides(self, mock_descriptor, kwargs):
        obj = mock_descriptor.create(**kwargs)
        assert obj.a == 101
        assert obj.b == 22

    def test_construct_from_base_config(self):
        obj = ConcreteInterface.Config(a=11, b=22)
        descriptor = evolver.base.ConfigDescriptor.model_validate(obj)
        assert descriptor.classinfo is ConcreteInterface
        assert descriptor.config == obj.model_dump()
        assert descriptor.config["a"] == 11
        assert descriptor.config["b"] == 22

    def test_construct_from_base_interface(self):
        obj = ConcreteInterface(a=11, b=22)
        descriptor = evolver.base.ConfigDescriptor.model_validate(obj)
        assert descriptor.classinfo is ConcreteInterface
        assert descriptor.config == obj.config
        assert descriptor.config["a"] == 11
        assert descriptor.config["b"] == 22

    def test_construct_from_static_cls(self):
        descriptor = evolver.base.ConfigDescriptor.model_validate(ConcreteInterface)
        assert descriptor.classinfo is ConcreteInterface
        assert descriptor.config == ConcreteInterface.Config().model_dump()
        assert descriptor.config["a"] == 2
        assert descriptor.config["b"] == 3

    def test_serialize_classinfo(self, mock_descriptor_as_json):
        descriptor = evolver.base.ConfigDescriptor.model_validate(mock_descriptor_as_json)
        assert isinstance(descriptor.classinfo, type)
        descriptor.model_dump_json() == mock_descriptor_as_json

    def test_classinfo_serialization(self):
        obj = ConcreteInterface.create()
        assert isinstance(obj.descriptor.classinfo, type)
        assert isinstance(obj.descriptor.model_dump()["classinfo"], type)
        assert isinstance(json.loads(obj.descriptor.model_dump_json())["classinfo"], str)
        assert isinstance(
            evolver.base.ConfigDescriptor(
                classinfo=json.loads(obj.descriptor.model_dump_json())["classinfo"]
            ).classinfo,
            type,
        )

    def test_classinfo_validator(self):
        with pytest.raises(pydantic.ValidationError):
            evolver.base.ConfigDescriptor(classinfo=int, config={})

    def test_from_file(self, tmp_path, mock_descriptor):
        file_path = tmp_path / "ConcreteInterfaceConfigDescriptor.yml"
        mock_descriptor.save(file_path)
        descriptor = evolver.base.ConfigDescriptor.model_validate(file_path)
        assert descriptor == mock_descriptor
        obj = descriptor.create()
        assert obj.a == 11
        assert obj.b == 22

    @pytest.mark.parametrize("shallow", (True, False))
    def test_nested(self, monkeypatch, shallow):
        if not shallow:
            monkeypatch.setattr(evolver.base._BaseConfig, "shallow_model_dump", lambda x: x.model_dump())

        config = {
            "stuff": {
                "classinfo": evolver.util.fully_qualified_name(Nested),
                "config": {
                    "stuff": {
                        "classinfo": evolver.util.fully_qualified_name(ConcreteInterface),
                        "config": {"a": 33, "b": 44},
                    }
                },
            }
        }
        obj = Nested.create(config)
        if shallow:
            assert isinstance(obj.stuff, Nested)
            assert isinstance(obj.stuff.stuff, ConcreteInterface)
        else:
            assert isinstance(obj.stuff, dict)


def test_require_all_fields():
    for field in ConcreteInterface.Config.model_fields.values():
        assert not field.is_required()

    ConcreteInterface.Config(a=1)

    @evolver.base.require_all_fields
    class ConfigWithoutDefaults(ConcreteInterface.Config): ...

    for field in ConfigWithoutDefaults.model_fields.values():
        assert field.is_required()

    with pytest.raises(pydantic.ValidationError, match="Field required"):
        ConfigWithoutDefaults(a=1)
