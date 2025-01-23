from fastapi import APIRouter, Request

from evolver.device import Experiment

router = APIRouter(prefix="/experiment", tags=["experiment"])


@router.get("/")
def get_experiments(request: Request) -> dict[str, Experiment]:
    return request.app.state.evolver.experiments


@router.get("/{experiment_name}/logs")
def get_experiment_logs(request: Request, experiment_name: str):
    evolver = request.app.state.evolver
    history = []
    for controller in evolver.experiments[experiment_name].controllers:
        if controller.name:
            history.append(evolver.history.get(name=controller.name, kinds=["log", "event"]))
    return history
