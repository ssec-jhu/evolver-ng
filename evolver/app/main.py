import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI

from evolver.base import require_all_fields
from evolver.device import Evolver, EvolverConfig
from evolver.settings import app_settings
from .. import __project__, __version__


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup:
    app.evolver = Evolver()
    if app_settings.LOAD_FROM_CONFIG_ON_STARTUP:
        app.evolver.update_config(EvolverConfig.load(app_settings.CONFIG_FILE))
    asyncio.create_task(evolver_async_loop())
    yield
    # Shutdown:
    ...


app = FastAPI(lifespan=lifespan)
app.evolver = None


@require_all_fields
class EvolverConfigWithoutDefaults(EvolverConfig):
    ...


@app.get("/")
async def describe_evolver():
    return {
        'config': app.evolver.config,
        'state': app.evolver.state,
        'last_read': app.evolver.last_read,
    }


@app.get('/state')
async def get_state():
    return {
        'state': app.evolver.state,
        'last_read': app.evolver.last_read,
    }


@app.post("/")
async def update_evolver(config: EvolverConfigWithoutDefaults):
    app.evolver.update_config(config)
    app.evolver.config.save(app_settings.CONFIG_FILE)


@app.get('/schema')
async def get_schema():
    return app.evolver.schema


@app.get('/history/{name}')
async def get_history(name: str):
    return app.evolver.history.get(name)


@app.get("/healthz")
async def healthz():
    return {"message": f"Running '{__project__}' ver: '{__version__}'"}


async def evolver_async_loop():
    while True:
        app.evolver.loop_once()
        await asyncio.sleep(app.evolver.config.interval)


def start():
    import uvicorn
    uvicorn.run(
        app,
        host=app_settings.HOST,
        port=app_settings.PORT,
        log_level="info"
    )


if __name__ == '__main__':
    start()
