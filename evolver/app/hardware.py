from typing import Any, Dict

from fastapi import Body, HTTPException, Path, FastAPI

from pydantic import BaseModel

hardware_router = FastAPI()


class Action(BaseModel):
    type: str  # Optional, depending on your needs
    payload: Dict[str, Any]


# endpoint used by the UI to present the user with a list of hardware to select from for calibration
@hardware_router.get("/")
def get_all_hardware():
    # see lifespan method on the main app, this is how we get the evolver instance in the calibration app
    evolver = hardware_router.state.evolver
    if not evolver:
        raise HTTPException(status_code=500, detail="Evolver not initialized")
    return evolver.hardware


# having selected a hardware by name user can now select vials to calibrate
@hardware_router.get("/{hardware_name}")
def get_hardware(hardware_name: str):
    evolver = hardware_router.state.evolver
    if not evolver:
        raise HTTPException(status_code=500, detail="Evolver not initialized")
    hardware_instance = evolver.get_hardware(hardware_name)
    if not hardware_instance:
        raise HTTPException(status_code=404, detail=f"Hardware '{hardware_name}' not found")
    return hardware_instance


# get the state of the calibrator for a hardware.
@hardware_router.get("/{hardware_name}/calibrator/state")
def get_calibration_status(hardware_name: str):
    evolver = hardware_router.state.evolver
    if not evolver:
        raise HTTPException(status_code=500, detail="Evolver not initialized")

    hardware_instance = evolver.get_hardware(hardware_name)
    if not hardware_instance:
        raise HTTPException(status_code=404, detail=f"Hardware '{hardware_name}' not found")

    calibrator = hardware_instance.calibrator
    if not calibrator:
        raise HTTPException(status_code=404, detail=f"Calibrator not found for '{hardware_name}'")

    return calibrator.state


class StartCalibrationProcedureRequest(BaseModel):
    selected_vials: None | list[int] = None


@hardware_router.post("/{hardware_name}/calibrator/init")
def start_calibration_procedure(hardware_name: str, request: StartCalibrationProcedureRequest):
    evolver = hardware_router.state.evolver
    if not evolver:
        raise HTTPException(status_code=500, detail="Evolver not initialized")

    hardware_instance = evolver.get_hardware(hardware_name)
    if not hardware_instance:
        raise HTTPException(status_code=404, detail=f"Hardware '{hardware_name}' not found")

    calibrator = hardware_instance.calibrator
    if not calibrator:
        raise HTTPException(status_code=404, detail=f"Calibrator not found for '{hardware_name}'")

    # Reset the calibrator state
    calibrator.state = calibrator.State()

    # Validate that all fields in the state are present in the request
    for field_name, field_info in calibrator.State.__fields__.items():
        if field_info.required and getattr(request, field_name, None) is None:
            raise HTTPException(
                status_code=400, detail=f"This calibration procedure requires '{field_name}' to be specified"
            )

    # Initialize the calibration procedure
    # Beware - this is technically a re-init as the calibration procedure on the calibrator is already initialized when
    # the class is init'ed by the framework, e.g. user made post request of a valid config object  to the '/' endpoint.
    calibrator.initialize_calibration_procedure()
    return {"message": f"Calibration procedure initialized for '{hardware_name}' and vials {request.selected_vials}"}


@hardware_router.post("/{hardware_name}/calibrator/dispatch")
def calibrate(hardware_name: str = Path(...), action: Action = Body(...)):
    evolver = hardware_router.state.evolver
    if not evolver:
        raise HTTPException(status_code=500, detail="Evolver not initialized")

    hardware_instance = evolver.get_hardware(hardware_name)
    if not hardware_instance:
        raise HTTPException(status_code=404, detail=f"Hardware '{hardware_name}' not found")

    calibrator = hardware_instance.calibrator
    if not calibrator:
        raise HTTPException(status_code=404, detail=f"Calibrator not found for '{hardware_name}'")

    try:
        # Dispatch the action to the calibration procedure
        new_state = calibrator.calibration_procedure.dispatch(action.payload)
        return {"state": new_state}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
