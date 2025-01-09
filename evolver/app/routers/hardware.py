from typing import Any, Dict, List

from fastapi import APIRouter, Body, Path, Request
from fastapi.params import Query
from pydantic import BaseModel

from evolver.app.exceptions import (
    CalibrationProcedureActionNotFoundError,
    CalibrationProcedureNotFoundError,
    CalibratorCalibrationDataNotFoundError,
    CalibratorNotFoundError,
    EvolverNotFoundError,
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
    if not (evolver := request.app.state.evolver):
        raise EvolverNotFoundError

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


# Start the calibration procedure for the selected hardware and vials,
# resume will init the procedure with the CalibrationData from the Calibrator.
# Where CalibrationData is the state of the procedure that has been persisted to the config file.
# If resume is False, the procedure state will reset.
@router.post("/{hardware_name}/calibrator/procedure/start")
def start_calibration_procedure(
    hardware_name: str,
    request: Request,
    resume: bool = Query(True),
):
    hardware_instance = get_hardware_instance(request, hardware_name)
    calibrator = hardware_instance.calibrator
    if not calibrator:
        raise CalibratorNotFoundError

    calibrator.create_calibration_procedure(
        selected_hardware=hardware_instance,
        resume=resume,
    )

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
        {
            "name": action.name,
            "description": action.description,
            "input_schema": action.FormModel.schema() if action.FormModel else None,
        }
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

    action_to_dispatch = None
    for a in calibration_procedure.get_actions():
        if a.name == action["action_name"]:
            action_to_dispatch = a
            break
    if not action_to_dispatch:
        raise CalibrationProcedureActionNotFoundError(action_name=action["action_name"])

    payload = action.get("payload", {})

    return calibration_procedure.dispatch(action_to_dispatch, payload)


# Get the current state of the calibration procedure
@router.get("/{hardware_name}/calibrator/procedure/state")
def get_calibrator_state(hardware_name: str, request: Request):
    hardware_instance = get_hardware_instance(request, hardware_name)
    if not (calibrator := hardware_instance.calibrator):
        raise CalibratorNotFoundError
    if not (calibration_procedure := calibrator.calibration_procedure):
        raise CalibrationProcedureNotFoundError

    return calibration_procedure.get_state()


# Undo the last calibration procedure action, reverting the state to the previous state
@router.post("/{hardware_name}/calibrator/procedure/undo")
def undo_calibration_procedure_action(hardware_name: str, request: Request):
    hardware_instance = get_hardware_instance(request, hardware_name)

    if not (calibrator := hardware_instance.calibrator):
        raise CalibratorNotFoundError
    calibration_procedure = calibrator.calibration_procedure
    return calibration_procedure.undo()


# Get the calibrator's CalibrationData, representing the state from the procedure that has been saved
# This data will appear in the config file even if the procedure is interupted. And will be used as the initial state when the procedure is resumed.
@router.get("/{hardware_name}/calibrator/data")
def get_calibration_data(hardware_name: str, request: Request):
    hardware_instance = get_hardware_instance(request, hardware_name)

    if not (calibrator := hardware_instance.calibrator):
        raise CalibratorNotFoundError
    if not calibrator.calibration_data:
        raise CalibratorCalibrationDataNotFoundError

    return calibrator.calibration_data


@router.get("/{hardware_name}/calibrator/output_transformer")
def get_calibration_output_transformer(hardware_name: str, request: Request):
    hardware_instance = get_hardware_instance(request, hardware_name)

    if not (calibrator := hardware_instance.calibrator):
        raise CalibratorNotFoundError

    if isinstance(calibrator.output_transformer, dict):
        return {i: transformer.config_model for i, transformer in calibrator.output_transformer.items()}

    return calibrator.output_transformer.config_model
