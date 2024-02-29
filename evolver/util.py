from pathlib import Path

import importlib
import os

from . import __project__  # Keep as relative for templating reasons.


def find_package_location(package=__project__):
    return Path(importlib.util.find_spec(package).submodule_search_locations[0])


def find_repo_location(package=__project__):
    return Path(find_package_location(package) / os.pardir)


def load_class_fqcn(fqcn):
    mod, cls = fqcn.rsplit('.', 1)
    module = importlib.import_module(mod)
    return getattr(module, cls)


def driver_from_descriptor(evolver, descriptor):
    cls = load_class_fqcn(descriptor.driver)
    conf = cls.Config.model_validate(descriptor.config)
    return cls(evolver, conf)
