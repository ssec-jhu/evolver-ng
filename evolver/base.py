import datetime
import logging
import os
from abc import ABC
from pathlib import Path
from typing import Any, Dict

import pydantic
import pydantic_core
import yaml
from pydantic._internal._validators import import_string

import evolver.util
from evolver.settings import settings
from evolver.types import CreatedTimestampField, ExpireField, ImportString


def require_all_fields(cls):
    """Decorate a model mutating it to one where all fields are required.

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


class _BaseConfig(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(extra="ignore", from_attributes=True)

    @classmethod
    def get_classinfo(cls):
        """The fully qualified classname for cls's container class (if one exists).
           Raises `TypeError` if parent class is not derived from BaseInterface.
        """
        fqn = evolver.util.fully_qualified_name(cls)
        containers = fqn.split('.')[:-1]
        container = ".".join(containers)
        container_class = import_string(container)
        if issubclass(container_class, BaseInterface):
            cls = container_class
        return f"{cls.__module__}.{cls.__qualname__}"

    @pydantic.model_serializer(mode="wrap", when_used='json')
    def to_descriptor(self, handler) -> dict:
        serialized_by_super = handler(self)
        if issubclass(self.__class__, ConfigDescriptor):
            return serialized_by_super
        return dict(classinfo=self.get_classinfo(), config=serialized_by_super)

    @classmethod
    def model_validate(cls, obj, *, strict=None, from_attributes=None, context=None):
        """Effectively the same as pydantic.BaseModel.model_validate() except that it automatically handles json, and
        conversion from instances of ``BaseConfig`` and ``BaseInterface`
        """
        if obj is None:
            return cls()
        elif isinstance(obj, os.PathLike):
            return cls.load(file_path=obj)
        elif isinstance(obj, (str, bytes, bytearray)):
            return cls.model_validate_json(obj, strict=strict, context=context)
        elif isinstance(obj, ConfigDescriptor):
            return super().model_validate(obj.config, strict=strict, from_attributes=from_attributes, context=context)
        elif isinstance(obj, BaseInterface):
            return super().model_validate(
                obj.config,  # Objects are responsible for their own conversion to config.
                strict=strict,
                from_attributes=from_attributes,
                context=context,
            )
        return super().model_validate(obj, strict=strict, from_attributes=from_attributes, context=context)

    @classmethod
    def load(cls, file_path: Path, encoding: str | None = None):
        """Loads the specified config file and return a new instance."""
        with open(file_path, encoding=encoding) as f:
            return cls.model_validate(yaml.safe_load(f))

    def save(self, file_path: Path, encoding: str | None = None):
        """Write out config as yaml file to specified file."""
        file_path = Path(file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, "w", encoding=encoding) as f:
            yaml.dump(self.model_dump(mode="json"), f)
        return Path(file_path)

    def shallow_model_dump(self):
        """
        When a ``config`` is a complete ``pydantic.BaseModel``, where all fields are adequately created. Any fields
        annotated as ``ConfigDescriptor`` will have automatically been converted to instances of ``ConfigDescriptor``,
        including lists & dicts of. One method to instantiate from this is to use ``cls(**config.model_dump())``,
        however, ``model_dump()`` will revert all of the above, resulting in any list & dicts of instances of
        ``ConfigDescriptor`` to be reverted back to native dicts. This is not desirable as we want to take advantage
        of pydantic having done the heavy lifting and keep config descriptors as actual instances so that they can
        be created calling ``ConfigDescriptor.create()``. ``model_dump()`` has no "shallow" semantics so we instead
        manually "dump" to dict using the following.
        """
        return dict(self)


class TimeStamp(_BaseConfig):
    created: pydantic.PastDatetime | None = CreatedTimestampField()
    expire: datetime.timedelta | None = ExpireField()


class BaseConfig(_BaseConfig):
    name: str | None = None


class ConfigDescriptor(_BaseConfig):
    classinfo: ImportString
    config: dict = {}

    @classmethod
    def model_validate(cls, obj, *args, **kwargs):
        """Effectively the same as pydantic.BaseModel.model_validate() except that it automatically handles conversion
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
            return super().model_validate(
                dict(classinfo=evolver.util.fully_qualified_name(obj), config=obj.Config().model_dump(mode="json")),
                *args,
                **kwargs,
            )
        elif isinstance(obj, BaseConfig) and (classinfo := obj.__pydantic_parent_namespace__.get("__qualname__")):
            return super().model_validate(
                dict(classinfo=f"{obj.__module__}.{classinfo}", config=obj.model_dump(mode="json")), *args, **kwargs
            )
        elif isinstance(obj, BaseInterface):
            return super().model_validate(dict(classinfo=obj.classinfo, config=obj.config), *args, **kwargs)
        return super().model_validate(obj, *args, **kwargs)

    def create(self, update: Dict[str, Any] | None = None, non_config_kwargs: Dict[str, Any] | None = None, **kwargs):
        """Create an instance of classinfo from a config.

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
            if update:
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
        return (
            self.classinfo(**config.shallow_model_dump(), **non_config_kwargs)
            if non_config_kwargs
            else self.classinfo(**config.shallow_model_dump())
        )

    @classmethod
    def load(cls, file_path: Path, encoding: str | None = None):
        """Loads the specified config file and return a new instance."""
        with open(file_path, encoding=encoding) as f:
            return cls.model_validate(yaml.safe_load(f))

    def save(self, file_path: Path, encoding: str | None = None):
        """Write out config as yaml file to specified file."""
        file_path = Path(file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, "w", encoding=encoding) as f:
            yaml.dump(self.model_dump(mode="json"), f)


class BaseInterface(ABC):
    """Base class for most classes.

    There are two instantiation patterns to choose from. The preferred path is using ``cls.create(config)`` where
    ``config`` fields will be validated against ``cls.Config`` using ``pydantic``. The alternative is normal
    instantiation i.e., ``cls()``.

    The normal path of ``cls()`` has some developer requirements. Whilst params can be passed to ``cls()`` as
    normally expected, keyword params explicitly specified in ``cls.__init__()`` are optional when they are also
    specified by ``cls.Config``. This feature reduces the need to duplicate both type annotations and default values
    for both config fields and ``__init__`` params. Instead, the base ``__init__`` introspects ``cls.Config``
    and auto assigns instance attributes of the same config field names. Keyword params explicitly specified in
    ``cls.__init__()`` are permitted however they must either be assigned in the class' ``__init__`` prior to
    calling ``super().__init__`` or passed as their field name strings via
    ``super().__init__(auto_config_ignore_fields=("a", "b")`` so that they are not assigned twice and possibly
    clobbered.

    Args:
        auto_config (bool): Turn on/off the above described auto instance attribute assignment functionality via
          ``cls.Config`` introspection. Defaults to ``True``.
        auto_config_ignore_fields (:obj: `list` of str): Specify config field names to NOT auto assign from
          introspecting ``cls.Config`` in the base ``__init__``. Note: any instance attributes assigned prior to
          calling ``super().__init__`` do not need to be passed using ``auto_config_ignore_fields``, only those that
          need assignment post ``super().__init__`` or for those that get assigned to asymmetric names, e.g., for
          initializing protected attributes accessed by properties that match config field names.
    """

    class Config(BaseConfig): ...

    @classmethod
    def create(cls, config: ConfigDescriptor | dict | str | None = None):
        """Create an instance from a config."""

        def validate_descriptor(descriptor: ConfigDescriptor):
            if not issubclass(cls, descriptor.classinfo):
                raise TypeError(
                    f"The given {ConfigDescriptor.__name__} for '{descriptor.classinfo}' is not compatible "
                    f"with this class '{cls.__qualname__}'"
                )
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
        return cls(**config.shallow_model_dump())

    def __init__(self, *args, name: str = None, auto_config=True, auto_config_ignore_fields=None, **kwargs):
        self.name = name or self.__class__.__name__
        self.logger = None
        self._setup_logger()

        if auto_config:
            # Don't unpack so that this can consume items from kwargs.
            self.auto_assign_attrs_from_config(kwargs, auto_config_ignore_fields=auto_config_ignore_fields)

        self.post_init_vars(*args, **kwargs)

        # Automatically walk over all vars and instantiate any that are ConfigDescriptors.
        # Note: To take advantage of this being here, and not having to explicitly call in child classes, the child's
        # ``__init__`` must call ``super().__init__()`` last, not first. If this instantiation order is not desirable,
        # simply call ``self.init_descriptors()`` explicitly from the child's ``__init__``.
        self.init_descriptors(**kwargs)

    def post_init_vars(self, *args, **kwargs):
        """A hook to override and perform additional initialization after instance attrs are assigned but before
        any ``ConfigDescriptor`` are converted to ``classinfo`` objects. I.e., after ``self.init_vars()`` and before
        ``self.init_descriptors()``.
        """
        ...

    def auto_assign_attrs_from_config(self, kwargs, auto_config_ignore_fields=None):
        """Auto instance attribute assignment functionality via ``cls.Config`` introspection.

        Instance attributes specified by ``self.Config`` are automatically unpacked from ``kwargs``, as passed into
        ``self.__init__``, and assigned. Config fields not present in ``kwargs`` are assigned if the have defaults,
        an exception is raised if they are required.

        Args:
            auto_config_ignore_fields (:obj: `list` of str): Specify config field names to NOT auto assign from
                introspecting ``cls.Config`` in the base ``__init__``. Note: any instance attributes assigned prior
                to calling ``super().__init__`` do not need to be passed using ``auto_config_ignore_fields``, only
                those that need assignment post ``super().__init__`` or for those that get assigned to asymmetric
                names, e.g., for initializing protected attributes accessed by properties that match config field
                names.
        """
        already_initialized_fields = vars(self)
        auto_config_ignore_fields = auto_config_ignore_fields if auto_config_ignore_fields is not None else []

        for k, v in self.Config.model_fields.items():
            # Ignore those already initialized.
            if k in auto_config_ignore_fields or k in already_initialized_fields:
                continue

            # Handle kwargs explicitly passed to ``__init__`.
            if k in kwargs:
                # Note: don't validate field, if validation is required, use ``cls.create()`` instead of ``cls()``.
                setattr(self, k, kwargs[k])
                # Consume kwarg similarly as python would such that post return, ``__init__(**kwargs)`` represents all
                # non-explicitly specified key word arguments as it normally would. This avoids interfering with
                # superfluous kwargs getting passed to other methods called from ``__init__``, e.g.,
                # ``init_descriptors``.
                del kwargs[k]
            else:
                if v.is_required():
                    raise KeyError(f"The field '{k}' is required but was missing upon instantiation.")
                else:
                    # Handle defaults.
                    setattr(self, k, v.get_default(call_default_factory=True))

    def init_descriptors(self, **non_config_kwargs):
        """Automatically walk over all vars and instantiate any that are ConfigDescriptors."""
        init_and_set_vars_from_descriptors(self, **non_config_kwargs)

    def _setup_logger(self):
        self.logger = logging.getLogger(f"{settings.DEFAULT_LOGGER}.{self.name}")

    @classmethod
    def __get_pydantic_core_schema__(cls, *args, **kwargs):
        return cls.Config.__get_pydantic_core_schema__(*args, **kwargs)

    @classmethod
    def __get_pydantic_json_schema__(cls, *args, **kwargs):
        return cls.Config.__get_pydantic_json_schema__(*args, **kwargs)

    @property
    def config(self) -> dict:
        """Return a dict of Config populated from instance attributes.

        Note: For convenience of converting back and forth from a ``ConfigDescriptor`` we return a ``dict`` rather
              than an instance of ``BaseConfig``.
        """
        return self.config_model.model_dump(mode="json")

    @property
    def config_json(self) -> str:
        """Return a JSON str from a Config populated from instance attributes."""
        return self.config_model.model_dump_json()

    @property
    def config_model(self) -> BaseConfig:
        """Return an instance of Config populated from instance attributes."""
        return self.Config.model_validate(vars(self))

    @property
    def descriptor(self) -> ConfigDescriptor:
        """Return a ``ConfigDescriptor``."""
        return ConfigDescriptor.model_validate(self)

    @property
    def classinfo(self):
        """Return the class' fully qualified name."""
        return evolver.util.fully_qualified_name(self.__class__)


def init_and_set_vars_from_descriptors(obj, **non_config_kwargs):
    """Instantiate object vars that are ConfigDescriptors and set them on the object.
    E.g., this can be called from a class' ``__init__`` as ``init_and_set_vars_from_descriptors(self)``.
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
