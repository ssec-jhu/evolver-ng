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

    def create(self):
        """ Create an instance of classinfo from a config. """
        cls = evolver.util.load_class_fqcn(self.classinfo)
        return cls.create(self.config)
