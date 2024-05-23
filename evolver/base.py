from abc import ABC
import logging

import pydantic
import pydantic_core


def require_all_fields(cls):
    """ Decorate a model mutating it to one where all fields are required.

        Example:
            ```python
            import pydantic
            from evolver.base import require_all_fields

            class MyModel(pydantic.BaseModel):
                a: int = 3

            @require_all_fields
            class MyModelWithoutDefaults(MyModel):
                ...
            ```
    """
    for field in cls.model_fields:
        # FieldInfo.is_required is specified as being conditionally only upon ``default`` & ``default_factory``.
        # see https://docs.pydantic.dev/latest/api/fields/#pydantic.fields.FieldInfo.is_required
        cls.model_fields[field].default = pydantic_core.PydanticUndefined
        cls.model_fields[field].default_factory = None

    cls.model_rebuild(force=True)
    return cls


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
    classinfo: pydantic.ImportString
    config: dict = {}

    def create(self, **kwargs):
        """ Create an instance of classinfo from a config.

            Args:
                kwargs (:obj:`dict`): Key-value pairs used to override contents of ``self.config``.
        """
        config = self.config.copy()
        config.update(kwargs)
        return self.classinfo.create(config)
