import logging
import threading
from contextlib import asynccontextmanager
from http import HTTPStatus

from fastapi import FastAPI
from fastapi.responses import JSONResponse, ORJSONResponse
from pydantic import ValidationError

import evolver.util
from evolver import __project__, __version__
from evolver.app.exceptions import CalibratorNotFoundError, HardwareNotFoundError, OperationNotSupportedError
from evolver.app.html_routes import html_app
from evolver.app.models import EventInfo, EvolverState, EvolverStateWithConfig, SchemaResponse
from evolver.app.routers import experiment, hardware
from evolver.base import require_all_fields
from evolver.device import Evolver
from evolver.history.interface import HistoryResult
from evolver.logutils import EVENT, LogInfo
from evolver.settings import app_settings, settings
from evolver.types import ImportString

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
        threading.Thread(target=evolver_thread_loop, daemon=True).start()
        yield

    # Shutdown:
    ...


app = FastAPI(lifespan=lifespan, default_response_class=ORJSONResponse)
app.state.evolver = None
app.state.trigger = threading.Event()


def evolver_thread_loop():
    while True:
        app.state.evolver.loop_once()
        app.state.trigger.wait(timeout=app.state.evolver.interval)
        app.state.trigger.clear()


@require_all_fields
class EvolverConfigWithoutDefaults(Evolver.Config): ...


@app.exception_handler(AttributeError)
async def attribute_error_handler(_, exc):
    raise OperationNotSupportedError(exc)


@app.exception_handler(ValidationError)
async def validation_error_handler(_, exc):
    return JSONResponse(status_code=HTTPStatus.UNPROCESSABLE_ENTITY, content=exc.errors())


app.include_router(hardware.router)
app.include_router(experiment.router)


@app.get("/", operation_id="describe")
async def describe_evolver() -> EvolverStateWithConfig:
    """Return the current applied configuration and state of the evolver.

    The state contains the latest readings from sensors, last read times and
    flag indicating if the evolver is currently active. The config returned by
    this endpoint can be used in a POST request to update the configuration.

    See also the `/state` endpoint which provides the current state of the
    evolver without the config.
    """
    return EvolverStateWithConfig(config=app.state.evolver.config_model, **(await get_state()).model_dump())


@app.get("/state", operation_id="state")
async def get_state() -> EvolverState:
    """Return the current state of the eVolver.

    The state refers to the sensor readings. This will be a dictionary mapping
    the hardware name, and within that typically will be a mapping of vial
    number to the sensor Output model (which is specific to the particular
    hardware being reported).

    This endpoint also contains a map of hardware name to the last read time of
    the hardware, which can be used to determine the freshness of the data.
    Additionally a flag `active` which is `True` if the control loop is enabled,
    meaning physical actuation may be performed.
    """
    return EvolverState(
        state=app.state.evolver.state,
        last_read=app.state.evolver.last_read,
        active=app.state.evolver.enable_control,
    )


@app.post("/", operation_id="update")
async def update_evolver(config: EvolverConfigWithoutDefaults):
    """Update the configuration of the eVolver.

    This endpoint requires all fields in the configuration to be explicitly
    provided, so does not support partial updates. To make a partial update,
    first obtain the full configuration using the `/` endpoint, modify the
    fields of interest, then POST the modified configuration back to this
    endpoint.

    note:
      Applying the configuration will replace the current eVolver in-memory
      object with a new one. Experiments will continue as normal, but any
      in-memory buffers within controllers will be lost. History will be
      preserved via the built-in history server, so typically this will not
      impact operations.
    """
    app.state.evolver = Evolver.create(config)
    app.state.evolver.config_model.save(app_settings.CONFIG_FILE)
    app.state.trigger.set()


@app.get("/schema/", response_model=SchemaResponse, operation_id="schema")
async def get_schema(classinfo: ImportString | None = evolver.util.fully_qualified_name(Evolver)) -> SchemaResponse:
    """Return json schema for the `Config` of given fully qualified class.

    If no class is provided, the json schema for the `Config` of the `Evolver`
    class is described (that which is returned in the `/` describe endpoint).

    This endpoint can be used when a client needs to know what fields to set on
    a particular hardware or controller when it is added to the system,
    particularly when fields are required. Given the class name of the
    component, this will return schema with the fields available to configure on
    that component.
    """
    return SchemaResponse(classinfo=classinfo)


@app.post("/history/", operation_id="history")
async def get_history(
    names: list[str] = None,
    kinds: list[str] | None = ["sensor"],
    t_start: float = None,
    t_stop: float = None,
    vials: list[int] | None = None,
    properties: list[str] | None = None,
    n_max: int = None,
) -> HistoryResult:
    """Get history data for the specified system components.

    The arguments herein are directly passed to the history server `get` method,
    see docs for `evolver.history.interface.History.get` for more information.

    The returned value is a `HistoryResult`, see
    `evolver.history.interface.HistoryResult` for more information.
    """
    return app.state.evolver.history.get(
        names=names, kinds=kinds, t_start=t_start, t_stop=t_stop, vials=vials, properties=properties, n_max=n_max
    )


@app.post("/event")
async def post_event(info: EventInfo):
    """Add an event to the history server.

    This puts a "event" kind with provided info into the history server. The
    info should contain a name, message and optionally a vial number it refers
    to and any auxiliary data to be stored with the event.

    These events can be subsequently retrieved using the `/history` endpoint,
    where they can be adding to plots or other visualizations.
    """
    full_name = f"{settings.DEFAULT_LOGGER}.{info.name}"
    logging.getLogger(full_name).log(EVENT, info.message, extra=LogInfo(vial=info.vial, **info.data))


@app.get("/healthz", operation_id="healthcheck")
async def healthz():
    return {
        "message": f"Running '{__project__}' ver: '{__version__}'",
        "active": app.state.evolver.enable_control,
        "name": app.state.evolver.name,
    }


@app.get("/calibration_status/")
async def calibration_status(name: str = None):
    """Return the status of calibration on the specified hardware.

    If no name is provided, the status of calibration on all hardware is
    returned as a map of hardware name to calibration status, where status is
    None if a calibrator doesn't exist on that hardware.

    If a name is provided and a calibrator does not exist, this returns a
    CalibratorNotFoundError.
    """
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


@app.post("/abort")
async def abort():
    """Abort the evolver.

    This will stop the control loop, thus preventing any further physical
    actuation of the system. The endpoint also calls the `abort` method of the
    eVolver manager, which in turn calls the `off` method of all hardware, to
    attempt to perform a clean shutdown.

    Abort does not stop sensor reads, so the state of the system can still be
    inquired to help ensure it arrived to a safe state.

    note:
        Shutting off hardware requires a command to be sent and acknowledged by
        the hardware, and thus it cannot be guaranteed that all hardware will
        successfully shut down. Physical intervention in the lab may be
        required.
    """
    app.state.evolver.abort()
    # Disable control/commit also in persistent config in case application needs to restart
    config = Evolver.Config.load(app_settings.CONFIG_FILE)
    config.enable_control = False
    config.save(app_settings.CONFIG_FILE)


@app.post("/start")
async def start():
    """Start the control loop after abort.

    This will re-enable the control loop, allowing the system to resume normal
    operation including physical actuation of the system.
    """
    config = Evolver.Config.load(app_settings.CONFIG_FILE)
    config.enable_control = True
    await update_evolver(config)


app.mount("/html", html_app)


def start_app():
    import uvicorn

    uvicorn.run(app, host=app_settings.HOST, port=app_settings.PORT, log_level="info")


if __name__ == "__main__":
    start_app()
