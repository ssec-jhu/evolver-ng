import importlib
import logging
import os
from pathlib import Path

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
