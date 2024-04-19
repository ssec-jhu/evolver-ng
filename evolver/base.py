from abc import ABC
import logging

import pydantic

import evolver.util


class BaseConfig(pydantic.BaseModel):
    name: str = None


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
            descriptor_class = config.import_classinfo()

            if not issubclass(cls, descriptor_class):
                raise TypeError(f"The given {ConfigDescriptor.__name__} for '{config.classinfo}' is not compatible "
                                f"with this class '{cls.__qualname__}'")

            config = cls.Config.model_validate(config.config)
        else:
            config = cls.Config.model_validate(config)

        obj = cls(**config.model_dump())
        obj._config = config
        return obj

    def __init__(self, name: str, *args, **kwargs):
        self.name = name if name else self.__class__.__name__
        self._setup_logger()
        self._config = None  # This is only populated if created using self.create() from a config.

    def _setup_logger(self):
        self.logger = logging.getLogger(self.name)
        ch = logging.StreamHandler()

        # TODO: #27 move to loglevel & format to settings file.
        ch.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

        ch.setFormatter(formatter)
        self.logger.addHandler(ch)


class ConfigDescriptor(pydantic.BaseModel):
    classinfo: str
    config: dict = {}

    def import_classinfo(self):
        return evolver.util.load_class_fqcn(self.classinfo)

    def create(self):
        """ Create an instance of classinfo from a config. """
        cls = self.import_classinfo()
        return cls.create(self.config)
