from abc import ABC

import pydantic


class BaseConfig(pydantic.BaseModel):
    ...


class BaseInterface(ABC):
    class Config(BaseConfig):
        ...

    @classmethod
    def create(cls, config=None):
        if config is None:
            config = cls.Config()
        elif not isinstance(config, BaseConfig):
            # Convert to BaseConfig instance.
            config = cls.Config.model_validate(config)

        obj = cls(**config.model_dump())
        obj._config = config
        return obj

    def __init__(self, *args, **kwargs):
        self._config = None  # This is only populated if created using self.create() from a config.
