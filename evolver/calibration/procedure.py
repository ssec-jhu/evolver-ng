from abc import ABC
from copy import deepcopy
from typing import Any, Dict, List

from pydantic import BaseModel, Field

from evolver.base import BaseInterface
from evolver.calibration.action import CalibrationAction


class CalibrationStateModel(BaseModel):
    """
    Model to represent the state of a calibration procedure. All procedures record their completed actions in this model.
    Along with the completed actions, the state of the calibration procedure (i.e. the data the actions have gathered) can be stored.
    The shape of this additional data is not fixed and therefore is not included in the model here.
    When considering adding attributes, note this model is shared by the Calibrator.CalibrationData class.

    Attributes:
        completed_actions (List[str]): A list of actions that have been completed during the calibration procedure.
        history: A list of previous states of the calibration procedure. Used to undo actions.
    """

    class Config:
        extra = "allow"

    completed_actions: List[str] = Field(default_factory=list)
    history: List["CalibrationStateModel"] = Field(default_factory=list)


class CalibrationProcedure(BaseInterface, ABC):
    class Config(BaseInterface.Config): ...

    def __init__(self, hardware, state=None, *args, **kwargs):
        """
        Initialize the CalibrationProcedure.

        Attributes:
            actions (list): The list of actions that can be executed in the calibration procedure.
                All actions are added to this list in the create_calibration_procedure method.
                Typically, a procedure is complete when all actions have been dispatched in sequence using the HTTP API.
            state (CalibrationStateModel): The state of the calibration procedure updated as actions are executed.
                The state can be saved and reloaded to continue the calibration procedure if interrupted.
                To save the state to the Calibrator.CalibrationData class, decorate an action's execute method with the @save decorator.
                Only state that is explicitly saved will be persisted, so it is important to save the state periodically.
            hardware (HardwareDriver): The hardware that the calibration procedure will interact with.

        Notes:
            Dispatching an action will update the state of the calibration procedure.

            The measured data that accumulates in procedure state is eventually used by the Calibrator's Transformer class
            to fit a model to the data. This can be done by defining a CalculateFit action in the procedure and dispatching it.
            Data stored in the CalibrationProcedure state should also be periodically saved to the Calibrator's CalibrationData class.
            That way CalibrationProcedure state can be saved and reloaded to continue the calibration procedure if interrupted.
            This can be done by defining a SaveProcedureState action in the procedure and dispatching it.
        """
        super().__init__(*args, **kwargs)
        self.actions = []
        self.state = CalibrationStateModel(**(state or {})).model_dump()
        self.hardware = hardware

    def add_action(self, action: CalibrationAction):
        if any(existing_action.name == action.name for existing_action in self.actions):
            raise ValueError(
                f"Action with name '{action.name}' already exists. Each action must have a unique name and functionality.  "
                f"If you want to repeat an action, any action can be dispatched multiple times using the HTTP api."
            )
        self.actions.append(action)

    def get_actions(self):
        return self.actions

    def get_state(self, *args, **kwargs):
        return self.state

    def undo(self):
        """
        Undo the last action that was dispatched in the calibration procedure.
        Note, if you dispatch an action decorated with the @save decorator, and then undo it, the saved representation of the procedure state will not reflect the undone action.
        """
        if len(self.state["history"]) > 0:
            self.state = self.state["history"].pop()
        return self.state

    def save(self):
        """
        Save the current state of the calibration procedure, to a file.
        The CalibrationData class, because it inherits from the Transformer class has a save method that saves its state to a file.
        NOTE: Currently this is everything in CalibrationData, maybe it should just be the "measured" attribute.
        """
        file_path = self.hardware.calibrator.calibration_file
        # calibration_file maybe none, in which case the save operation must fail with an error message.
        if file_path is None:
            raise ValueError("calibration_file attribute is not set on the Calibrator config.")
        self.hardware.calibrator.calibration_data.measured = self.state
        self.hardware.calibrator.calibration_data.save(file_path)
        return self.state

    def dispatch(self, action: CalibrationAction, payload: Dict[str, Any]):
        if payload is not None and action.FormModel.model_fields != {}:
            payload = action.FormModel(**payload)
        previous_state = deepcopy(self.state)
        updated_state = action.execute(self.state, payload)
        updated_state["completed_actions"].append(action.name)
        updated_state["history"].append(previous_state)
        self.state = updated_state
        return self.state
