from typing import Any, Dict, List

import pydantic
from fastapi import APIRouter, Body, HTTPException, Path, Request
from pydantic import BaseModel

from evolver.app.exceptions import (
    CalibrationProcedureActionInvalidPayloadError,
    CalibrationProcedureActionNotFoundError,
    CalibratorCalibrationProcedureFailedToInitializeError,
    CalibratorNotFoundError,
    HardwareNotFoundError,
)
from evolver.hardware.interface import HardwareDriver

router = APIRouter(prefix="/hardware", tags=["hardware"], responses={404: {"description": "Not found"}})


class Action(BaseModel):
    type: str
    payload: Dict[str, Any]


class StartCalibrationProcedureRequest(BaseModel):
    selected_vials: None | List[int] = None


def get_hardware_instance(request: Request, hardware_name: str) -> HardwareDriver:
    if not (hardware_instance := request.app.state.evolver.hardware.get(hardware_name)):
        raise HardwareNotFoundError
    return hardware_instance


@router.get("/")
def get_all_hardware(request: Request):
    evolver = request.app.state.evolver
    if not evolver:
        raise HTTPException(status_code=500, detail="Evolver not initialized")

    hardware_outputs = {name: driver.get() for name, driver in evolver.hardware.items()}
    return hardware_outputs


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
@router.post("/{hardware_name}/calibrator/procedure/start")
def start_calibration_procedure(
    hardware_name: str,
    request: Request,
    initial_state: Dict | None,
):
    hardware_instance = get_hardware_instance(request, hardware_name)
    calibrator = hardware_instance.calibrator
    if not calibrator:
        raise CalibratorNotFoundError
    if hasattr(calibrator, "initialize_calibration_procedure"):
        calibrator.initialize_calibration_procedure(
            selected_hardware=hardware_instance,
            initial_state=initial_state,
        )
    else:
        raise CalibratorCalibrationProcedureFailedToInitializeError
    return calibrator.calibration_procedure.get_state()


# Get available actions for the calibration procedure
@router.get("/{hardware_name}/calibrator/procedure/actions")
def get_calibrator_actions(hardware_name: str, request: Request):
    hardware_instance = get_hardware_instance(request, hardware_name)
    calibrator = hardware_instance.calibrator
    if not calibrator:
        raise CalibratorNotFoundError
    calibration_procedure = calibrator.calibration_procedure
    actions = [
        {"name": action.model.name, "description": action.model.description}
        for action in calibration_procedure.get_actions()
    ]
    return {"actions": actions}


# Dispatch an action to the calibration procedure
@router.post("/{hardware_name}/calibrator/procedure/dispatch")
def dispatch_calibrator_action(request: Request, hardware_name: str = Path(...), action: dict = Body(...)):
    hardware_instance = get_hardware_instance(request, hardware_name)
    calibrator = hardware_instance.calibrator
    if not calibrator:
        raise CalibratorNotFoundError

    calibration_procedure = calibrator.calibration_procedure
    print("HERE!!!")
    action_to_dispatch = next(
        (a for a in calibration_procedure.get_actions() if a.model.name == action["action_name"]), None
    )

    print("ALL_ACTION_NAMES: ", [a.model.name for a in calibration_procedure.get_actions()])
    print("ACTION_TO_DISPATCH: ", action_to_dispatch)
    print("ACTION_NAME: ", action["action_name"])
    if not action_to_dispatch:
        raise CalibrationProcedureActionNotFoundError(action_name=action["action_name"])

    try:
        payload = action.get("payload", {})
        new_state = calibration_procedure.dispatch(action_to_dispatch, payload)
    except pydantic.ValidationError as e:
        raise CalibrationProcedureActionInvalidPayloadError(errors=e.errors())

    return {"state": new_state}


# Get the current state of the calibration procedure
@router.get("/{hardware_name}/calibrator/procedure/state")
def get_calibrator_state(hardware_name: str, request: Request):
    hardware_instance = get_hardware_instance(request, hardware_name)
    calibrator = hardware_instance.calibrator
    if not calibrator:
        raise CalibratorNotFoundError
    calibration_procedure = calibrator.calibration_procedure
    return calibration_procedure.get_state()


@router.get("/{hardware_name}/calibrator/data")
def get_calibration_data(hardware_name: str, request: Request):
    hardware_instance = get_hardware_instance(request, hardware_name)

    calibrator = hardware_instance.calibrator
    if not calibrator:
        raise CalibratorNotFoundError

    calibration_data = calibrator.calibration_data
    if not calibration_data:
        raise HTTPException(status_code=404, detail=f"Calibration data not found for '{hardware_name}'")

    return calibration_data
