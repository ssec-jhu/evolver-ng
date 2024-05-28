import importlib
import os
from pathlib import Path

from . import __project__  # Keep as relative for templating reasons.


def find_package_location(package=__project__):
    return Path(importlib.util.find_spec(package).submodule_search_locations[0])


def find_repo_location(package=__project__):
    return Path(find_package_location(package) / os.pardir)


def fully_qualified_name(cls):
    """ The fully qualified classname for cls. """
    return f"{cls.__module__}.{cls.__qualname__}"
