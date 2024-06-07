from typing import Any

import pydantic

from evolver.base import BaseConfig, BaseInterface, ImportString


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
