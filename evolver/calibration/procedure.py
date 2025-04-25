from abc import ABC
from typing import Any, Dict

from evolver.base import BaseInterface
from evolver.calibration.action import CalibrationAction
from evolver.calibration.interface import CalibrationStateModel


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
        self.state = CalibrationStateModel.model_validate(state)
        self.state.started = True
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

    def get_action(self, name):
        actions = [action for action in self.actions if action.name == name]
        if len(actions) == 0:
            raise ValueError(f"Action with name '{name}' not found.")
        return actions[0]

    def get_state(self, *args, **kwargs):
        return self.state

    def undo(self):
        """
        Undo the last action that was dispatched in the calibration procedure.
        """
        if len(self.state.history) > 0:
            # Restore the previous state but keep the current history
            # to avoid losing undo history
            previous_state = self.state.history.pop()
            current_history = self.state.history

            # Set state to previous state
            self.state = previous_state

            # Restore the history without the last item which we just popped
            self.state.history = current_history

        return self.state

    def save(self):
        """
        Save the current state of the calibration procedure, to a file.
        The calibration_data attribute on the Calibrator, because it is a CalibrationStateModel, it inherits from the Transformer class has a save method that saves its state to a file.
        The file the state is saved to is defined in the Calibrator's config, specifically calibrator.dir/calibrator.calibration_file.
        """
        file_path = self.hardware.calibrator.procedure_file
        if file_path is None:
            # This indicates the user started a procedure and completed some actions and now wants to save it but no procedure file exists...
            # techincally this should be an impossible state, since starting or resuming a procedure using the HTTP endpoint guarantees the procedure_file attribute exists on config.
            raise ValueError("procedure_file attribute is not set on the Calibrator config.")
        self.hardware.calibrator.calibration_data = self.state
        self.hardware.calibrator.calibration_data.save(file_path)
        return self.state

    def apply(self):
        """
        Apply the calibration by updating the calibration_file to match the saved state of the calibration procedure.

        This sets the calibration_file to the value of procedure_file.

        Since updating configuration re-initializes the evolver object, this will result in
        loading the calibration state data stored in the calibration_file location and calling init_transformers through the standard mechanisms.

        See the /{hardware_name}/calibrator/procedure/apply HTTP endpoint for further details.
        """
        # call save method this saves procedure state to the procedure_file attribute.
        self.save()
        # now save the procedure state to the calibration_file attribute
        # see: /{hardware_name}/calibrator/procedure/apply HTTP endpoint for some setup
        file_path = self.hardware.calibrator.calibration_file
        if file_path is None:
            # techincally this should be an impossible state, since applying a procedure using the HTTP endpoint guarantees the procedure_file attribute exists on config.
            raise ValueError("calibration_file attribute is not set on the Calibrator config.")
        self.hardware.calibrator.calibration_data = self.state

        self.hardware.calibrator.calibration_data.save(file_path)
        # Clear procedure_file to indicate that the procedure is complete and has been applied
        self.hardware.calibrator.procedure_file = None

        return self.state

    def dispatch(self, action: CalibrationAction, payload: Dict[str, Any]):
        if payload is not None and action.FormModel.model_fields != {}:
            payload = action.FormModel(**payload)
        # Create a shallow copy of the previous state without the history
        previous_state = self.state.model_dump()
        previous_state_no_history = {k: v for k, v in previous_state.items() if k != "history"}

        updated_state = action.execute(self.state, payload)
        updated_state.completed_actions.append(action.name)

        # Store only the state without nested history
        updated_state.history.append(CalibrationStateModel.model_validate(previous_state_no_history))
        self.state = updated_state
        return self.state
