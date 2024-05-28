from abc import ABC
from collections import defaultdict
import logging
from pathlib import Path
from typing import Annotated, Any, Dict

import pydantic
import pydantic_core
import yaml

import evolver.util


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


# pydantics import string alone does not generate a schema, which breaks openapi
# docs. We wrap it to set schema explicitly.
ImportString = Annotated[
    pydantic.ImportString, pydantic.WithJsonSchema({'type': 'string', 'description': 'fully qualified class name'})
]


class _BaseConfig(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(extra="ignore",
                                       from_attributes=True)

    @classmethod
    def model_validate(cls, obj, *, strict=None, from_attributes=None, context=None):
        """ Effectively the same as pydantic.BaseModel.model_validate() except that it automatically handles json, and
            conversion from instances of ``BaseConfig`` and ``BaseInterface`
        """
        if obj is None:
            return cls()
        elif isinstance(obj, (str,  bytes, bytearray)):
            return cls.model_validate_json(obj, strict=strict, context=context)
        elif isinstance(obj, ConfigDescriptor):
            return super().model_validate(obj.config, strict=strict, from_attributes=from_attributes, context=context)
        elif isinstance(obj, BaseInterface):
            return super().model_validate(obj.config,  # Objects are responsible for their own conversion to config.
                                          strict=strict,
                                          from_attributes=from_attributes,
                                          context=context)
        return super().model_validate(obj, strict=strict, from_attributes=from_attributes, context=context)


class BaseConfig(_BaseConfig):
    name: str | None = None


class ConfigDescriptor(_BaseConfig):
    classinfo: ImportString
    config: dict = {}

    @classmethod
    def model_validate(cls, obj, *args, **kwargs):
        """ Effectively the same as pydantic.BaseModel.model_validate() except that it automatically handles conversion
            from instances of ``BaseConfig`` and ``BaseInterface``.
        """

        # Note: ``ConfigDescriptor.config`` is an ordinary dict, without type mappings between keys and values, i.e.,
        # unlike pydantic model fields. Any nested ``ConfigDescriptor`` in config, when converted to a dict using
        # ``model_dump()`` will have their classinfo keys remain as their imported classes rather than a fqn str.
        # The issue with these no longer being models is that ``classinfo`` will just be a normal key and not an
        # ``ImportString``. Subsequent serialization will not be possible as it doesn't go via
        # ``ImportString._Serialize()``. To address this, we always use ``model_dump(mode="json")`` such
        # ``classinfo`` has been correctly serialized. This is not ideal, nor performant, though the latter is not an
        # issue for this code base.
        # TODO: Rethink ConfigDescriptor.config type, as an ordinary dict doesn't ensure that its contents is
        #  serializable. The very point of the pydantic framework is to solve this issue.

        if isinstance(obj, type) and issubclass(obj, BaseInterface):
            return super().model_validate(dict(classinfo=evolver.util.fully_qualified_name(obj),
                                               config=obj.Config().model_dump(mode="json")),
                                          *args,
                                          **kwargs)
        elif isinstance(obj, BaseConfig) and (classinfo := obj.__pydantic_parent_namespace__.get("__qualname__")):
            return super().model_validate(dict(classinfo=f"{obj.__module__}.{classinfo}",
                                               config=obj.model_dump(mode="json")),
                                          *args,
                                          **kwargs)
        elif isinstance(obj, BaseInterface):
            return super().model_validate(dict(classinfo=obj.classinfo, config=obj.config), *args, **kwargs)
        return super().model_validate(obj, *args, **kwargs)

    def create(self,
               update: Dict[str, Any] | None = defaultdict(),
               non_config_kwargs: Dict[str, Any] | None = defaultdict(),
               **kwargs):
        """ Create an instance of classinfo from a config.

            Args:
                update (:obj:`dict`): Key-value pairs used to override contents of ``self.config``. These get validated.
                non_config_kwargs (:obj:`dict`): Key-value pairs passed to ``classinfo`` upon instantiation. These are
                                                 not validated.
                **kwargs: Synonymous with ``update``. Values here take precedence over any in update, i.e., ``config``
                          is updated using ``update`` first and then ``kwargs``, thus ``kwargs`` will clobber keys also
                          present in ``update``.
        """
        # Update config from kwargs.
        if update or kwargs:
            config = self.config.copy()
            config.update(update)
            config.update(kwargs)
        else:
            config = self.config

        # Instantiate classinfo.Config.
        # Note: We directly create a ``Config`` rather than just return ``self.classinfo.create(config)``:
        # 1) for perf (since ``self.classinfo.create()`` will try to turn this in to a ``ConfigDescriptor``).
        # 2) ``self.config`` must a be a dict representing ``self.Classinfo.Config`` and NOT a dict representing a
        #    ``ConfigDescriptor`` (which ``self.classinfo.create()`` allows).
        config = self.classinfo.Config.model_validate(config)  # Note: we don't pass self due to update from kwargs.

        # Return an instance of classinfo.
        return self.classinfo(**config.model_dump(), **non_config_kwargs)

    @classmethod
    def load(cls, file_path: Path, encoding: str | None = None):
        """Loads the specified config file and return a new instance."""
        with open(file_path, encoding=encoding) as f:
            return cls.model_validate(yaml.safe_load(f))

    def save(self, file_path: Path, encoding: str | None = None):
        """Write out config as yaml file to specified file."""
        with open(file_path, 'w', encoding=encoding) as f:
            yaml.dump(self.model_dump(mode='json'), f)


class BaseInterface(ABC):
    """ Base class for most classes. """

    class Config(BaseConfig):
        ...

    @classmethod
    def create(cls, config: ConfigDescriptor | dict | str | None = None):
        """ Create an instance from a config. """

        def validate_descriptor(descriptor: ConfigDescriptor):
            if not issubclass(cls, descriptor.classinfo):
                raise TypeError(f"The given {ConfigDescriptor.__name__} for '{descriptor.classinfo}' is not compatible "
                                f"with this class '{cls.__qualname__}'")
            return cls.Config.model_validate(descriptor, context=dict(extra="forbid"))

        # We first try to create a valid Config instance and then from that create an instance of cls.
        if config is None:
            # Empty config.
            config = cls.Config()
        elif isinstance(config, ConfigDescriptor):
            config = validate_descriptor(config)
        else:
            # Next handle dict | str, which could be that representing a Config or a ConfigDescriptor.
            # First see if config is actually a descriptor by trying to create one, since it's only fields are limited
            # to classinfo and config.
            try:
                descriptor = ConfigDescriptor.model_validate(config, context=dict(extra="forbid"))
                config = validate_descriptor(descriptor)
            except pydantic.ValidationError:
                config = cls.Config.model_validate(config)

        # Instantiate cls from config.
        # Note: ``config`` is now a complete ``pydantic.BaseModel``, where all fields are adequately created. Any fields
        # annotated as ``ConfigDescriptor`` will have automatically been converted to instances of ``ConfigDescriptor``,
        # including lists & dicts of. One method to instantiate is ``cls(**config.model_dump())``, however,
        # ``model_dump()`` will revert all of the above, resulting in any list & dicts of instances of
        # ``ConfigDescriptor`` to be reverted back to native dicts. This is not desirable as we want to take advantage
        # of pydantic having done the heavy lifting and keep config descriptors as actual instances so that they can
        # be created calling ``ConfigDescriptor.create()``. ``model_dump()`` has no "shallow" semantics so we instead
        # manually "dump" to dict using the following.
        return cls(**dict(config))

    def __init__(self, *args, name: str = None, **kwargs):
        self.name = name or self.__class__.__name__
        self.logger = None
        self._setup_logger()

        # Automatically walk over all vars and instantiate any that are ConfigDescriptors.
        # Note: To take advantage of this being here, and not having to explicitly call in child classes, the child's
        # ``__init__`` must call ``super().__init__()`` last, not first. If this instantiation order is not desirable,
        # simply call ``self.init_descriptors()`` explicitly from the child's ``__init__``.
        self.init_descriptors(**kwargs)

    def init_descriptors(self, **non_config_kwargs):
        """ Automatically walk over all vars and instantiate any that are ConfigDescriptors. """
        init_and_set_vars_from_descriptors(self, **non_config_kwargs)

    def _setup_logger(self):
        self.logger = logging.getLogger(self.name)
        ch = logging.StreamHandler()

        # TODO: #27 move to loglevel & format to settings file.
        ch.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

        ch.setFormatter(formatter)
        self.logger.addHandler(ch)

    @classmethod
    def __get_pydantic_core_schema__(cls, *args, **kwargs):
        return cls.Config.__get_pydantic_core_schema__(*args, **kwargs)

    @classmethod
    def __get_pydantic_json_schema__(cls, *args, **kwargs):
        return cls.Config.__get_pydantic_json_schema__(*args, **kwargs)

    @property
    def config(self) -> dict:
        """ Return a dict of Config populated from instance attributes.

            Note: For convenience of converting back and forth from a ``ConfigDescriptor`` we return a ``dict`` rather
                  than an instance of ``BaseConfig``.
        """
        return self.config_model.model_dump(mode="json")

    @property
    def config_json(self) -> str:
        """ Return a JSON str from a Config populated from instance attributes. """
        return self.config_model.model_dump_json()

    @property
    def config_model(self) -> BaseConfig:
        """ Return a dict of Config populated from instance attributes. """
        return self.Config.model_validate(vars(self))

    @property
    def descriptor(self) -> ConfigDescriptor:
        return ConfigDescriptor.model_validate(self)

    @property
    def classinfo(self):
        return evolver.util.fully_qualified_name(self.__class__)


def init_and_set_vars_from_descriptors(obj, **non_config_kwargs):
    """ Instantiate object vars that are ConfigDescriptors and set them on the object.
        E.g., this can be called from a classes ``__init__`` as ``init_and_set_vars_from_descriptors(self)``.
    """
    for key, value in vars(obj).items():
        if isinstance(value, ConfigDescriptor):
            setattr(obj, key, value.create(non_config_kwargs=non_config_kwargs))
        elif isinstance(value, list):
            for i, x in enumerate(value):
                if isinstance(x, ConfigDescriptor):
                    value[i] = x.create(non_config_kwargs=non_config_kwargs)
        elif isinstance(value, dict):
            for k, v in value.items():
                if isinstance(v, ConfigDescriptor):
                    value[k] = v.create(non_config_kwargs=non_config_kwargs)
                    value[k] = v.create(non_config_kwargs=non_config_kwargs)
