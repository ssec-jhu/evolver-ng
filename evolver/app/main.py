import asyncio
from fastapi import FastAPI
from evolver.device import Evolver, EvolverConfig
from .. import __project__, __version__


app = FastAPI()
evolver = Evolver()


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
async def update_evolver(config: EvolverConfig):
    evolver.update_config(config)


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


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
