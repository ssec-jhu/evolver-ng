from fastapi import APIRouter, Request, HTTPException

from evolver.device import Experiment
from evolver.settings import app_settings

router = APIRouter(prefix="/dev", tags=["dev"])


@router.get("/loop_once")
def get_experiments(request: Request) -> dict[str, Experiment]:
    return request.app.state.evolver.experiments


@router.post("/loop_once")
async def dev_loop_once(request: Request):
    print("FOO")
    """Development endpoint to manually trigger a control loop iteration. Useful for testing and debugging. Only available in DEV_MODE."""
    if not app_settings.DEV_MODE:
        raise HTTPException(status_code=403, detail="Only available in development mode")

    try:
        request.app.state.evolver.loop_once()
        return {"status": "success", "message": "Loop iteration completed"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
