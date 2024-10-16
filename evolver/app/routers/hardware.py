from typing import Any, Dict, List

import pydantic
from fastapi import APIRouter, Body, HTTPException, Path, Request
from pydantic import BaseModel

from evolver.app.exceptions import CalibratorNotFoundError, HardwareNotFoundError
from evolver.hardware.interface import HardwareDriver

router = APIRouter(prefix="/hardware", tags=["hardware"], responses={404: {"description": "Not found"}})


class Action(BaseModel):
    type: str
    payload: Dict[str, Any]


class StartCalibrationProcedureRequest(BaseModel):
    selected_vials: None | List[int] = None


# Utility function to fetch the evolver and hardware instance
def get_hardware_instance(request: Request, hardware_name: str) -> HardwareDriver:
    if not (hardware_instance := request.app.state.evolver.hardware.get(hardware_name)):
        raise HardwareNotFoundError
    return hardware_instance


# Endpoint used by the UI to present the user with a list of hardware to select from for calibration
@router.get("/")
def get_all_hardware(request: Request):
    evolver = request.app.state.evolver
    if not evolver:
        raise HTTPException(status_code=500, detail="Evolver not initialized")

    hardware_outputs = {name: driver.get() for name, driver in evolver.hardware.items()}
    return hardware_outputs


# Having selected a hardware by name, the user can now select vials to calibrate
@router.get("/{hardware_name}")
def get_hardware(hardware_name: str, request: Request):
    hardware_instance = get_hardware_instance(request, hardware_name)
    return hardware_instance.get()


@router.post("/{hardware_name}/set")
def hardware_set(hardware_name: str, request: Request, data: dict | list[dict], commit: bool = False):
    hardware_instance = get_hardware_instance(request, hardware_name)
    input_model = hardware_instance.Input
    if isinstance(data, list):
        inputs = [input_model.model_validate(i) for i in data]
    else:
        inputs = [input_model.model_validate(data)]

    for input in inputs:
        hardware_instance.set(input)
    if commit:
        hardware_instance.commit()


@router.post("/{hardware_name}/commit")
def hardware_commit(hardware_name: str, request: Request):
    hardware_instance = get_hardware_instance(request, hardware_name)
    hardware_instance.commit()


# Start the calibration procedure for the selected hardware and vials
@router.post("/{hardware_name}/calibrator/start")
def start_calibration_procedure(
    hardware_name: str, request: Request, calibration_request: StartCalibrationProcedureRequest
):
    hardware_instance = get_hardware_instance(request, hardware_name)
    calibrator = hardware_instance.calibrator
    if not calibrator:
        raise HTTPException(status_code=404, detail=f"Calibrator not found for '{hardware_name}'")

    calibrator.initialize_calibration_procedure(
        selected_hardware=hardware_instance,
        selected_vials=calibration_request.selected_vials,
        evolver=request.app.state.evolver,
    )

    return calibrator.state


# Get available actions for the calibration procedure
@router.get("/{hardware_name}/calibrator/actions")
def get_calibrator_actions(hardware_name: str, request: Request):
    hardware_instance = get_hardware_instance(request, hardware_name)
    calibrator = hardware_instance.calibrator
    if not calibrator:
        raise HTTPException(status_code=404, detail=f"Calibrator not found for '{hardware_name}'")

    calibration_procedure = calibrator.calibration_procedure
    actions = [
        {"name": action.name, "description": action.description} for action in calibration_procedure.get_actions()
    ]

    return {"actions": actions}


# Dispatch an action to the calibration procedure
@router.post("/{hardware_name}/calibrator/dispatch")
def dispatch_calibrator_action(request: Request, hardware_name: str = Path(...), action: dict = Body(...)):
    hardware_instance = get_hardware_instance(request, hardware_name)
    calibrator = hardware_instance.calibrator
    if not calibrator:
        raise HTTPException(status_code=404, detail=f"Calibrator not found for '{hardware_name}'")

    calibration_procedure = calibrator.calibration_procedure

    action_to_dispatch = next((a for a in calibration_procedure.get_actions() if a.name == action["action_name"]), None)

    if not action_to_dispatch:
        raise HTTPException(status_code=404, detail=f"Action '{action['action_name']}' not found")

    try:
        payload = action["payload"]
        new_state = calibration_procedure.dispatch(action_to_dispatch, payload)
    except pydantic.ValidationError as e:
        raise HTTPException(status_code=422, detail=f"Invalid payload: {e.errors()}")

    return {"state": new_state}


# Get the current state of the calibrator for a hardware
@router.get("/{hardware_name}/calibrator/state")
def get_calibrator_state(hardware_name: str, request: Request):
    hardware_instance = get_hardware_instance(request, hardware_name)
    calibrator = hardware_instance.calibrator
    if not calibrator:
        raise CalibratorNotFoundError

    return calibrator.state
