from typing import Dict

from evolver.calibration.action import DisplayInstructionAction
from evolver.calibration.interface import IndependentVialBasedCalibrator
from evolver.calibration.procedure import CalibrationProcedure
from evolver.calibration.standard.actions.temperature import (
    CalculateFitAction,
    ProcedureState,
    RawValueAction,
    ReferenceValueAction,
    SaveProcedureStateAction,
)
from evolver.calibration.standard.polyfit import LinearTransformer
from evolver.hardware.interface import HardwareDriver


class TemperatureCalibrator(IndependentVialBasedCalibrator):
    """
    A calibrator for temperature sensors, extending the `IndependentVialBasedCalibrator` to allow for independent
    calibration per vial with configurable input and output transformers.

    Attributes:
        input_transformer (dict): A dictionary of transformers for processing sensor input data on a per-vial basis.
        output_transformer (dict): A dictionary of transformers for processing sensor output data on a per-vial basis.
        default_input_transformer (Transformer): The default transformer for input data, set to `LinearTransformer` if
            no specific transformer is provided.
        default_output_transformer (Transformer): The default transformer for output data, also defaulting to
            `LinearTransformer` if none is specified.

    Parameters:
        input_transformer (Transformer, optional): The transformer to use by default for input data. Defaults to
            `LinearTransformer` if none is provided.
        output_transformer (Transformer, optional): The transformer to use by default for output data, also defaults to
            `LinearTransformer` if none is provided.
        *args: Additional arguments to pass to the parent `IndependentVialBasedCalibrator`.
        **kwargs: Additional keyword arguments to pass to the parent `IndependentVialBasedCalibrator`.
    """

    def __init__(self, input_transformer=None, output_transformer=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.input_transformer = {}
        self.output_transformer = {}
        self.default_input_transformer = input_transformer or LinearTransformer()
        self.default_output_transformer = output_transformer or LinearTransformer()

    def initialize_calibration_procedure(
        self,
        selected_hardware: HardwareDriver,
        initial_state: Dict,
        *args,
        **kwargs,
    ):
        try:
            initial_state = ProcedureState.model_validate(initial_state)
        except TypeError:
            raise ValueError(
                "Calibration procedure initial state is invalid, procedure must be initialized with a list of vials that the procedure will run on"
            )

        selected_vials = initial_state.selected_vials

        for vial in selected_vials:
            self.input_transformer[vial] = self.default_input_transformer
            self.output_transformer[vial] = self.default_output_transformer

        calibration_procedure = CalibrationProcedure("Temperature Calibration", initial_state=initial_state)
        calibration_procedure.add_action(
            DisplayInstructionAction(description="Fill each vial with 15ml water", name="fill_vials_instruction")
        )
        for vial in selected_vials:
            calibration_procedure.add_action(
                ReferenceValueAction(
                    hardware=selected_hardware,
                    vial_idx=vial,
                    description=f"Use a thermometer to measure the real temperature in vial: {vial}.",
                    name=f"measure_vial_{vial}_temperature",
                )
            )
            calibration_procedure.add_action(
                RawValueAction(
                    hardware=selected_hardware,
                    vial_idx=vial,
                    description=f"The hardware will now read the raw output values of vial: {vial}'s temperature sensor.",
                    name=f"read_vial_{vial}_raw_output",
                )
            )

        for vial in selected_vials:
            calibration_procedure.add_action(
                CalculateFitAction(
                    hardware=selected_hardware,
                    vial_idx=vial,
                    description=f"Calculate the fit for the vial: {vial}'s temperature sensor",
                    name=f"calculate_vial_{vial}_fit",
                )
            )

        calibration_procedure.add_action(
            SaveProcedureStateAction(
                hardware=selected_hardware,
                description="Save the calibration procedure state",
                name="save_calibration_procedure_state",
            )
        )

        self.calibration_procedure = calibration_procedure
