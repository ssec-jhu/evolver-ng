from fastapi import APIRouter, Request

from evolver.device import Experiment

router = APIRouter(prefix="/experiment", tags=["experiment"])


@router.get("/")
def get_experiments(request: Request) -> dict[str, Experiment]:
    return request.app.state.evolver.experiments


@router.get("/{experiment_name}/logs")
def get_experiment_logs(request: Request, experiment_name: str):
    evolver = request.app.state.evolver
    controllers = evolver.experiments[experiment_name].controllers
    names = [c.name for c in controllers if c.name]
    return evolver.history.get(names=names, kinds=["log", "event"])


@router.get("/{experiment_name}")
def get_experiment_overview(request: Request, experiment_name: str):
    evolver = request.app.state.evolver
    experiment = evolver.experiments[experiment_name]

    return {
        "config": experiment,
        "logs": get_experiment_logs(request, experiment_name),
    }
