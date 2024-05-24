import importlib
import os
import yaml
from pathlib import Path

from evolver.device import Evolver, EvolverConfig

from . import __project__  # Keep as relative for templating reasons.


def find_package_location(package=__project__):
    return Path(importlib.util.find_spec(package).submodule_search_locations[0])


def find_repo_location(package=__project__):
    return Path(find_package_location(package) / os.pardir)


def load_config_for_evolver(evolver: Evolver, configfile: Path):
    """Loads the specified config file and applies to evolver."""
    if configfile.exists():
        with open(configfile) as f:
            evolver.update_config(EvolverConfig.model_validate(yaml.load(f, yaml.SafeLoader)))


def save_evolver_config(config: EvolverConfig, configfile: Path):
    """Write out evolver config as yaml file to specified file."""
    with open(configfile, 'w') as f:
        yaml.dump(config.model_dump(mode='json'), f)
