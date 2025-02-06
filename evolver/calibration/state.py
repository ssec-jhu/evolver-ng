from typing import Any, Dict, List

from pydantic import BaseModel, Field


class CalibrationStateModel(BaseModel):
    """
    Model to represent the state of a calibration procedure. All procedures record their completed actions, and history of actions in this model.
    The data collected by the calibration procedure (i.e. the data the actions have gathered, that's used as input to the Hardware.input/outputTransformer methods) is also stored here.

    Attributes:
        started (bool): A flag to indicate if the calibration procedure has been initialized, used by the front end to determine procedure controls to display.
        completed_actions (List[str]): A list of actions that have been completed during the calibration procedure.
        history: A list of previous states of the calibration procedure. Used to undo actions.
        measured (Dict[Any, Any]): A dictionary of data collected by the calibration procedure. This data is used by the Transformer class to fit a model to the data. For example, a temperature calibrator might collect raw and reference temperature data for each vial.
    """

    class Config:
        extra = "allow"

    completed_actions: List[str] = Field(default_factory=list)
    history: List["CalibrationStateModel"] = Field(default_factory=list)
    started: bool = False
    measured: Dict[Any, Any] = {}
