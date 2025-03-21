from typing import Any, Dict, List

from fastapi import APIRouter, Body, Path, Request
from fastapi.params import Query
from pydantic import BaseModel
import datetime

from evolver.app.exceptions import (
    CalibrationProcedureActionNotFoundError,
    CalibrationProcedureNotFoundError,
    CalibratorCalibrationDataNotFoundError,
    CalibratorNotFoundError,
    CalibratorProcedureApplyError,
    CalibratorProcedureSaveError,
    EvolverNotFoundError,
    HardwareNotFoundError,
)
from evolver.hardware.interface import HardwareDriver
from evolver.settings import app_settings, settings

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
    procedure_file: str = Query(None),
):
    """Start a calibration procedure for the specified hardware.

    Args:
        hardware_name: Name of the hardware to calibrate
        resume: If True, resume from existing procedure state. If False, start a new procedure
                and require a procedure_file name.
        procedure_file: Optional, file name to save the procedure state to, useful for testing the api if provided the hardware's procedure_file attribute in .

    Returns:
        The initial state of the calibration procedure.
    """
    hardware_instance = get_hardware_instance(request, hardware_name)
    calibrator = hardware_instance.calibrator
    if not calibrator:
        raise CalibratorNotFoundError

    if resume:
        # Resuming, ensure we have a procedure file defined in config
        if calibrator.procedure_file is None:
            raise CalibrationProcedureNotFoundError()
    else:
        # Not resuming (new procedure)
        # Update the calibrator's procedure_file to be the one specified by the user in the request param if it's present
        # otherwise use a default.

        if procedure_file is not None:
            calibrator.procedure_file = procedure_file
        else:
            calibrator.procedure_file = Path(
                f"{hardware_instance.name}_{datetime.datetime.now().strftime(settings.DATETIME_PATH_FORMAT)}"
            ).with_suffix(".yml")

        # Save the updated configuration file
        request.app.state.evolver.config_model.save(app_settings.CONFIG_FILE)

    # Create the calibration procedure
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

    if not (calibration_procedure := getattr(calibrator, "calibration_procedure", None)):
        return {"started": False}

    actions = [
        {
            "name": action.name,
            "description": action.description,
            "input_schema": action.FormModel.schema() if action.FormModel else None,
        }
        for action in calibration_procedure.get_actions()
    ]
    return {"actions": actions, "started": calibration_procedure.get_state().started}


# Dispatch an action to the calibration procedure
@router.post("/{hardware_name}/calibrator/procedure/dispatch")
def dispatch_calibrator_action(request: Request, hardware_name: str = Path(...), action: dict = Body(...)):
    hardware_instance = get_hardware_instance(request, hardware_name)
    calibrator = hardware_instance.calibrator
    if not calibrator:
        raise CalibratorNotFoundError

    if not (calibration_procedure := getattr(calibrator, "calibration_procedure", None)):
        return {"started": False}

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

    if not (calibration_procedure := getattr(calibrator, "calibration_procedure", None)):
        return {"started": False}

    return calibration_procedure.get_state()


# Undo the last calibration procedure action, reverting the state to the previous state
@router.post("/{hardware_name}/calibrator/procedure/undo")
def undo_calibration_procedure_action(hardware_name: str, request: Request):
    hardware_instance = get_hardware_instance(request, hardware_name)

    if not (calibrator := hardware_instance.calibrator):
        raise CalibratorNotFoundError

    if not (calibration_procedure := getattr(calibrator, "calibration_procedure", None)):
        return {"started": False}

    return calibration_procedure.undo()


@router.post("/{hardware_name}/calibrator/procedure/save")
def save_calibration_procedure(hardware_name: str, request: Request):
    hardware_instance = get_hardware_instance(request, hardware_name)

    if not (calibrator := hardware_instance.calibrator):
        raise CalibratorNotFoundError

    if not (calibration_procedure := getattr(calibrator, "calibration_procedure", None)):
        return {"started": False}
    try:
        calibration_procedure.save()
    except Exception:
        raise CalibratorProcedureSaveError

    return calibration_procedure.get_state()


@router.post("/{hardware_name}/calibrator/procedure/apply")
def apply_calibration_procedure(
    hardware_name: str,
    request: Request,
    calibration_file: str,  # Required parameter to specify calibration file path
):
    """Apply the calibration procedure to update the calibrator configuration.

    When trying to understand both the Calibrator.calibration_file and Calibrator.procedure_file,
    calibration_file is a complete version of procedure_file, whereas the latter can be incomplete.

    One way to think about procedure_file is as ephemeral memory, or a "buffer" used to store the in-progress procedure data.
    When all actions that constitute a procedure are complete, that procedure is eligible to be "applied", which means
    that its state is copied to the calibration_file and the data stored there is sufficient to calibrate the hardware it is
    associated with whenever the device is initialized.

    On which note: since the configuration is reinitialized by calling save -
    self.hardware.calibrator.calibration_data.save(file_path)
    the evolver object will be reinitialized directly when this endpoint is invoked, and transformers initialized.

    """

    hardware_instance = get_hardware_instance(request, hardware_name)

    if not (calibrator := hardware_instance.calibrator):
        raise CalibratorNotFoundError

    if not (calibration_procedure := getattr(calibrator, "calibration_procedure", None)):
        return {"started": False}

    # Update the calibrator's configuration with the provided calibration_file
    calibrator.calibration_file = calibration_file

    try:
        # Apply will save the procedure state to the calibration_file
        calibration_procedure.apply()
        # Save the updated configuration
        request.app.state.evolver.config_model.save(app_settings.CONFIG_FILE)
    except ValueError as e:
        raise CalibratorProcedureApplyError(detail=str(e))
    except Exception as e:
        raise CalibratorProcedureApplyError(detail=str(e))

    return calibration_procedure.get_state()


# Get the calibrator's CalibrationData, representing the state from the procedure that has been saved
# This data will appear in the config file even if the procedure is interrupted. And will be used as the initial state when the procedure is resumed.
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
