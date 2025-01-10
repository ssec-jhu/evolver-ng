import importlib
import logging
import os
from pathlib import Path

import pydantic

from evolver import __project__
from evolver.settings import settings


def find_package_location(package=__project__):
    return Path(importlib.util.find_spec(package).submodule_search_locations[0])


def find_repo_location(package=__project__):
    return Path(find_package_location(package) / os.pardir)


def fully_qualified_name(cls):
    """The fully qualified classname for cls."""
    return f"{cls.__module__}.{cls.__qualname__}"


def setup_logging(level=settings.LOG_LEVEL, format=settings.LOG_FORMAT):
    logging.basicConfig(level=level, format=format)


def filter_data_properties(data, properties=[]):
    return {k: v for k, v in data.items() if not properties or k in properties}


def import_string(dotted_path: str) -> type:
    """Import and convert a dotted path to its actual class type."""

    # Utilize pydantic._internal._validators.import_string validation without illegally importing protected methods.
    class Wrapper(pydantic.BaseModel):
        import_string: pydantic.ImportString

    return Wrapper.model_validate(dict(import_string=dotted_path)).import_string
