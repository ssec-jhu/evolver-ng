import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI

import evolver.util
from evolver import __project__, __version__
from evolver.app.exceptions import CalibratorNotFoundError, HardwareNotFoundError
from evolver.app.models import SchemaResponse
from evolver.base import ImportString, require_all_fields
from evolver.device import Evolver
from evolver.settings import app_settings

# Setup logging.
evolver.util.setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup:
    if app_settings.LOAD_FROM_CONFIG_ON_STARTUP:
        app.state.evolver = Evolver.create(Evolver.Config.load(app_settings.CONFIG_FILE))
    else:
        app.state.evolver = Evolver.create()
    asyncio.create_task(evolver_async_loop())
    yield
    # Shutdown:
    ...


app = FastAPI(lifespan=lifespan)
app.state.evolver = None


@require_all_fields
class EvolverConfigWithoutDefaults(Evolver.Config): ...


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


@app.get("/history/{name}", operation_id="history")
async def get_history(name: str):
    return app.state.evolver.history.get(name)


@app.get("/healthz", operation_id="healthcheck")
async def healthz():
    return {"message": f"Running '{__project__}' ver: '{__version__}'"}


async def evolver_async_loop():
    while True:
        app.state.evolver.loop_once()
        await asyncio.sleep(app.state.evolver.interval)


@app.get("/calibration_status/")
async def calibration_status(name: str = None):

    # TODO: semantic change: this needs to return calibration status/staleness. I.e., calibration date (that when last
    # calibrated) and then a delta compared to some configurable time expired, e.g., 6 months, and then a bool for
    # the semantics of this delta to whether it's stale or ok to still use.

    if not name:
        return app.state.evolver.calibration_status

    if not (driver := app.state.evolver.hardware.get(name)):
        raise HardwareNotFoundError

    if calibrator := getattr(driver, "calibrator", None):
        return calibrator.is_calibrated
    else:
        raise CalibratorNotFoundError


@app.post("/calibrate/{name}")
async def calibrate(name: str):
    if not (driver := app.state.evolver.hardware.get(name)):
        raise HardwareNotFoundError

    if not (calibrator := getattr(driver, "calibrator", None)):
        raise CalibratorNotFoundError

    # TODO: Do we warn if calibrator.is_calibrated == True?

    # TODO: This is just a placeholder.
    return calibrator.run_calibration_procedure()


def start():
    import uvicorn

    uvicorn.run(app, host=app_settings.HOST, port=app_settings.PORT, log_level="info")


if __name__ == "__main__":
    start()
