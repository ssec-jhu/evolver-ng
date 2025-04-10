from typing import Any

import pydantic

from evolver.base import BaseConfig, BaseInterface
from evolver.device import Evolver
from evolver.types import ImportString


class SchemaResponse(pydantic.BaseModel):
    classinfo: ImportString
    config: dict | None = None
    input: dict | None = None
    output: dict | None = None

    def model_post_init(self, __context: Any) -> None:
        if issubclass(self.classinfo, BaseConfig):
            self.config = self.classinfo.model_json_schema()
        elif issubclass(self.classinfo, BaseInterface):
            self.config = self.classinfo.Config.model_json_schema()

            if hasattr(self.classinfo, "Input") and issubclass(self.classinfo.Input, pydantic.BaseModel):
                self.input = self.classinfo.Input.model_json_schema()

            if hasattr(self.classinfo, "Output") and issubclass(self.classinfo.Output, pydantic.BaseModel):
                self.output = self.classinfo.Output.model_json_schema()


class EventInfo(pydantic.BaseModel):
    name: str
    message: str
    vial: int | None = None
    data: dict = {}

    @pydantic.field_validator("data", mode="before")
    @classmethod
    def validate_data(cls, v):
        return {} if v is None else v


class EvolverState(pydantic.BaseModel):
    state: dict
    last_read: dict
    active: bool


class EvolverStateWithConfig(EvolverState):
    config: Evolver.Config
