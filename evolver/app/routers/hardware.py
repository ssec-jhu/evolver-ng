from typing import Any, Dict

from fastapi import Body, HTTPException, Path, Request, APIRouter

from pydantic import BaseModel

router = APIRouter(prefix="/hardware", tags=["hardware"], responses={404: {"description": "Not found"}})


class Action(BaseModel):
    type: str  # Optional, depending on your needs
    payload: Dict[str, Any]


# endpoint used by the UI to present the user with a list of hardware to select from for calibration
@router.get("/")
def get_all_hardware(request: Request):
    evolver = request.app.state.evolver
    if not evolver:
        raise HTTPException(status_code=500, detail="Evolver not initialized")
    # Get hardware outputs
    hardware_outputs = {name: driver.get() for name, driver in evolver.hardware.items()}

    return hardware_outputs


# having selected a hardware by name user can now select vials to calibrate
@router.get("/{hardware_name}")
def get_hardware(hardware_name: str, request: Request):
    evolver = request.app.state.evolver
    if not evolver:
        raise HTTPException(status_code=500, detail="Evolver not initialized")
    hardware_instance = evolver.get_hardware(hardware_name)
    if not hardware_instance:
        raise HTTPException(status_code=404, detail=f"Hardware '{hardware_name}' not found")
    hardware_outputs = hardware_instance.get()
    return hardware_outputs


# get the state of the calibrator for a hardware.
@router.get("/{hardware_name}/calibrator/state")
def get_calibrator_state(hardware_name: str, request: Request):
    evolver = request.app.state.evolver
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


@router.post("/{hardware_name}/calibrator/start")
def start_calibration_procedure(
    hardware_name: str, request: Request, calibration_request: StartCalibrationProcedureRequest
):
    evolver = request.app.state.evolver
    if not evolver:
        raise HTTPException(status_code=500, detail="Evolver not initialized")

    hardware_instance = evolver.get_hardware(hardware_name)
    if not hardware_instance:
        raise HTTPException(status_code=404, detail=f"Hardware '{hardware_name}' not found")

    calibrator = hardware_instance.calibrator
    if not calibrator:
        raise HTTPException(status_code=404, detail=f"Calibrator not found for '{hardware_name}'")

    calibrator.initialize_calibration_procedure(**calibration_request.model_dump())
    # Return the current state of the calibrator's calibration procedure
    return calibrator.state


@router.post("/{hardware_name}/calibrator/actions")
def get_calibrator_actions(hardware_name: str, request: Request):
    evolver = request.app.state.evolver
    if not evolver:
        raise HTTPException(status_code=500, detail="Evolver not initialized")

    hardware_instance = evolver.get_hardware(hardware_name)
    if not hardware_instance:
        raise HTTPException(status_code=404, detail=f"Hardware '{hardware_name}' not found")

    calibrator = hardware_instance.calibrator
    if not calibrator:
        raise HTTPException(status_code=404, detail=f"Calibrator not found for '{hardware_name}'")

    # Get the calibration procedure and list all actions
    calibration_procedure = calibrator.calibration_procedure
    actions = calibration_procedure.get_actions()

    # Extract action names and descriptions to return to the frontend
    actions_list = [{"name": action.name, "description": action.description} for action in actions]

    return {"actions": actions_list}


@router.post("/{hardware_name}/calibrator/dispatch")
def dispatch_calibrator_action(request: Request, hardware_name: str = Path(...), action: dict = Body(...)):
    evolver = request.app.state.evolver
    if not evolver:
        raise HTTPException(status_code=500, detail="Evolver not initialized")

    hardware_instance = evolver.get_hardware(hardware_name)
    if not hardware_instance:
        raise HTTPException(status_code=404, detail=f"Hardware '{hardware_name}' not found")

    calibrator = hardware_instance.calibrator
    if not calibrator:
        raise HTTPException(status_code=404, detail=f"Calibrator not found for '{hardware_name}'")

    # Get the calibration procedure
    calibration_procedure = calibrator.calibration_procedure

    # Find the action by name in the calibration procedure
    action_to_dispatch = next((a for a in calibration_procedure.get_actions() if a.name == action["action_name"]), None)

    if not action_to_dispatch:
        raise HTTPException(status_code=404, detail=f"Action '{action['action_name']}' not found")

    try:
        # Dispatch the action to the calibration procedure with the given payload
        new_state = calibration_procedure.dispatch(action_to_dispatch, action["payload"])

        # Return the updated state of the calibration procedure
        return {"state": new_state}

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
