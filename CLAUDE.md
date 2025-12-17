# CLAUDE.md - Development Reference

## Build/Test Commands
- Run all tests: `tox`
- Run specific test: `tox -e test -- -xvs evolver/path/to/test_file.py::TestClass::test_function`
- Code formatting: `tox -e format`
- Lint code: `tox -e check-style`
- Security check: `tox -e check-security`
- Run dev server: `tox -e dev` (with config) or `EVOLVER_LOAD_FROM_CONFIG_ON_STARTUP=false tox -e dev` (without)
- Generate OpenAPI: `tox -e generate_openapi`

## Code Style Guidelines
- Line length: 120 characters max
- Documentation: Google docstring style
- Type hints: Required for all functions/methods
- Import ordering: Use `ruff` import sorting (`ruff check --select I --fix .`)
- Error handling: Use custom exceptions from `evolver.app.exceptions`
- Naming: snake_case for variables/functions, PascalCase for classes
- Config classes: Use `BaseConfig` subclasses with `pydantic` models for validation
- Tests: Each module should have corresponding unit tests in a `tests` directory
- Avoid using NaN values - use `None` instead (JSON compatibility)