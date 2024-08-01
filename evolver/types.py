import datetime
from functools import partial
from typing import Annotated

import pydantic

# pydantics import string alone does not generate a schema, which breaks openapi
# docs. We wrap it to set schema explicitly.
ImportString = Annotated[
    pydantic.ImportString, pydantic.WithJsonSchema({"type": "string", "description": "fully qualified class name"})
]


CreatedTimestampField = partial(
    pydantic.Field, description="The creation timestamp", default_factory=datetime.datetime.now
)


ExpireField = partial(
    pydantic.Field,
    default=datetime.timedelta.max,
    description="The amount of time after which the associated object is considered stale. "
    "`datetime.timedelta.max` := forever (the default).",
)
