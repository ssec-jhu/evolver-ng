import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI

import evolver.util
from evolver import __project__, __version__
from evolver.app.exceptions import CalibratorNotFoundError, HardwareNotFoundError
from evolver.app.html_routes import html_app
from evolver.app.models import SchemaResponse
from evolver.base import require_all_fields
from evolver.device import Evolver
from evolver.history.interface import HistoryResult
from evolver.settings import app_settings
from evolver.types import ImportString

# Import routers
from .routers import hardware

# Setup logging.
evolver.util.setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup:
    if app_settings.LOAD_FROM_CONFIG_ON_STARTUP:
        app.state.evolver = Evolver.create(Evolver.Config.load(app_settings.CONFIG_FILE))
    else:
        app.state.evolver = Evolver.create()

    with app.state.evolver:
        asyncio.create_task(evolver_async_loop())
        yield

    # Shutdown:
    ...


app = FastAPI(lifespan=lifespan)
app.state.evolver = None


@require_all_fields
class EvolverConfigWithoutDefaults(Evolver.Config): ...


app.include_router(hardware.router)


@app.get("/", operation_id="describe")
async def describe_evolver():
    return {
        "config": app.state.evolver.config_model,
        "state": app.state.evolver.state,
        "last_read": app.state.evolver.last_read,
    }


@app.get("/state", operation_id="state")
async def get_state():
    return {
        "state": app.state.evolver.state,
        "last_read": app.state.evolver.last_read,
    }


@app.post("/", operation_id="update")
async def update_evolver(config: EvolverConfigWithoutDefaults):
    app.state.evolver = Evolver.create(config)
    app.state.evolver.config_model.save(app_settings.CONFIG_FILE)


@app.get("/schema/", response_model=SchemaResponse, operation_id="schema")
async def get_schema(classinfo: ImportString | None = evolver.util.fully_qualified_name(Evolver)) -> SchemaResponse:
    return SchemaResponse(classinfo=classinfo)


@app.get("/history/", operation_id="history")
@app.post("/history/", operation_id="history")
async def get_history(
    name: str = None,
    t_start: float = None,
    t_stop: float = None,
    vials: list[int] | None = None,
    properties: list[str] | None = None,
    n_max: int = None,
) -> HistoryResult:
    return app.state.evolver.history.get(
        name=name, t_start=t_start, t_stop=t_stop, vials=vials, properties=properties, n_max=n_max
    )


@app.get("/healthz", operation_id="healthcheck")
async def healthz():
    return {"message": f"Running '{__project__}' ver: '{__version__}'"}


async def evolver_async_loop():
    while True:
        app.state.evolver.loop_once()
        await asyncio.sleep(app.state.evolver.interval)


@app.get("/calibration_status/")
async def calibration_status(name: str = None):
    if not name:
        return app.state.evolver.calibration_status

    if not (driver := app.state.evolver.hardware.get(name)):
        raise HardwareNotFoundError

    if calibrator := getattr(driver, "calibrator", None):
        return calibrator.status
    else:
        raise CalibratorNotFoundError


@app.post("/calibrate/{name}")
async def calibrate(name: str, data: dict = None):
    if not (driver := app.state.evolver.hardware.get(name)):
        raise HardwareNotFoundError

    if not (calibrator := getattr(driver, "calibrator", None)):
        raise CalibratorNotFoundError

    # TODO: This is just a placeholder.
    return calibrator.run_calibration_procedure(data)  # TODO: or **data?


app.mount("/html", html_app)


def start():
    import uvicorn

    uvicorn.run(app, host=app_settings.HOST, port=app_settings.PORT, log_level="info")


if __name__ == "__main__":
    start()
