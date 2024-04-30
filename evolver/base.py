from abc import ABC
import logging

import pydantic


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
            if not issubclass(cls, config.classinfo):
                raise TypeError(f"The given {ConfigDescriptor.__name__} for '{config.classinfo}' is not compatible "
                                f"with this class '{cls.__qualname__}'")

            config = cls.Config.model_validate(config.config)
        else:
            config = cls.Config.model_validate(config)

        obj = cls(**config.model_dump())
        obj._config = config
        return obj

    def __init__(self, *args, name: str = None, **kwargs):
        self.name = name if name else self.__class__.__name__
        self.logger = None
        self._config = None  # This is only populated if created using self.create() from a config.

        self._setup_logger()

    def _setup_logger(self):
        self.logger = logging.getLogger(self.name)
        ch = logging.StreamHandler()

        # TODO: #27 move to loglevel & format to settings file.
        ch.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

        ch.setFormatter(formatter)
        self.logger.addHandler(ch)


class ConfigDescriptor(pydantic.BaseModel):
    classinfo: pydantic.ImportString
    config: dict = {}

    def create(self):
        """ Create an instance of classinfo from a config. """
        return self.classinfo.create(self.config)


def init_and_set_vars_from_descriptors(obj):
    """ Instantiate object vars that are ConfigDescriptors and set them on the object.
        E.g., this can be called from a classes ``__init__`` as ``init_and_set_vars_from_descriptors(self)``.
    """
    for key, value in vars(obj).items():
        if isinstance(value, ConfigDescriptor):
            setattr(obj, value.create())
