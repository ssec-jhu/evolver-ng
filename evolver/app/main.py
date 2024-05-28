import asyncio
from fastapi import FastAPI

from evolver.base import require_all_fields
from evolver.device import Evolver, EvolverConfig
from evolver.settings import app_settings
from .. import __project__, __version__


app = FastAPI()
evolver = Evolver()


@require_all_fields
class EvolverConfigWithoutDefaults(EvolverConfig):
    ...


@app.get("/")
async def describe_evolver():
    return {
        'config': evolver.config,
        'state': evolver.state,
        'last_read': evolver.last_read,
    }


@app.get('/state')
async def get_state():
    return {
        'state': evolver.state,
        'last_read': evolver.last_read,
    }


@app.post("/")
async def update_evolver(config: EvolverConfigWithoutDefaults):
    evolver.update_config(config)
    evolver.config.save(app_settings.CONFIG_FILE)


@app.get('/schema')
async def get_schema():
    return evolver.schema


@app.get('/history/{name}')
async def get_history(name: str):
    return evolver.history.get(name)


@app.get("/healthz")
async def healthz():
    return {"message": f"Running '{__project__}' ver: '{__version__}'"}


async def evolver_async_loop():
    while True:
        evolver.loop_once()
        await asyncio.sleep(evolver.config.interval)


@app.on_event('startup')
async def start_evolver_loop():
    asyncio.create_task(evolver_async_loop())


@app.on_event('startup')
async def load_config():
    evolver.update_config(EvolverConfig.load(app_settings.CONFIG_FILE))


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
