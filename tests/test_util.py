from evolver import __project__, __version__
from evolver.util import find_package_location, find_repo_location, import_string


def test_find_repo_location():
    repo_path = find_repo_location()
    assert repo_path
    assert (repo_path / __project__).exists()


def test_find_package_location():
    pkg_path = find_package_location()
    assert pkg_path
    assert pkg_path.exists()
    assert pkg_path.is_dir()
    assert pkg_path.name == __project__


def test_version_file():
    pkg_path = find_package_location()
    assert pkg_path.exists()
    version_file = pkg_path / "_version.py"
    assert version_file.exists()


def test_version():
    assert __version__


def test_project():
    assert __project__


def test_import_string():
    import_type = import_string("evolver.device.Evolver")
    assert isinstance(import_type, type)

    from evolver.device import Evolver

    assert import_type is Evolver
