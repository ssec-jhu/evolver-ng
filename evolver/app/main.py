import asyncio
import os
import yaml
from fastapi import FastAPI
from pathlib import Path

from evolver.base import require_all_fields
from evolver.device import Evolver, EvolverConfig
from .. import __project__, __version__


EVOLVER_CONFIG_FILE=Path('evolver.yml')  # in current directory
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
    with open(EVOLVER_CONFIG_FILE, 'w') as f:
        yaml.dump(config.model_dump(mode='json'), f)

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


def load_config_file():
    if EVOLVER_CONFIG_FILE.exists():
        with open(EVOLVER_CONFIG_FILE) as f:
            evolver.update_config(EvolverConfig.model_validate(yaml.load(f, yaml.SafeLoader)))

def start():
    import uvicorn
    uvicorn.run(
        app,
        host=os.getenv("EVOLVER_HOST", "127.0.0.1"),
        port=int(os.getenv("EVOLVER_PORT", 8000)),
        log_level="info"
    )


if __name__ == '__main__':
    load_config_file()
    start()
