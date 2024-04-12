from abc import ABC

import pydantic

import evolver.util


class BaseConfig(pydantic.BaseModel):
    ...


class BaseInterface(ABC):
    """ Base class for most classes. """

    class Config(BaseConfig):
        ...

    @classmethod
    def create(cls, config=None):
        """ Create an instance from a config. """
        if config is None:
            config = cls.Config()
        elif isinstance(config, str):
            config = cls.Config.model_validate_json(config)
        elif isinstance(config, ConfigDescriptor):
            type_error = TypeError(f"The given {ConfigDescriptor.__name__} for '{config.classinfo}' is not compatible "
                                   f"with this class '{cls.__qualname__}'")
            try:
                descriptor_class = config.import_classinfo()
            except ImportError as error:
                raise type_error from error

            if not issubclass(cls, descriptor_class):
                raise type_error

            config = cls.Config.model_validate(config.config)
        else:
            config = cls.Config.model_validate(config)

        obj = cls(**config.model_dump())
        obj._config = config
        return obj

    def __init__(self, *args, **kwargs):
        self._config = None  # This is only populated if created using self.create() from a config.


class ConfigDescriptor(pydantic.BaseModel):
    classinfo: str
    config: dict = {}

    def import_classinfo(self):
        return evolver.util.load_class_fqcn(self.classinfo)

    def create(self):
        """ Create an instance of classinfo from a config. """
        cls = self.import_classinfo()
        return cls.create(self.config)
