import time
from collections import defaultdict
from typing import Optional

from pydantic import BaseModel

from evolver.calibration.action import CalibrationAction
from evolver.calibration.interface import CalibrationStateModel
from evolver.calibration.procedure import CalibrationProcedure


class SimpleAction(CalibrationAction):
    """A simple action that increments a counter in the state."""

    class FormModel(BaseModel):
        pass

    def __init__(self, action_id: int, *args, **kwargs):
        name = f"action_{action_id}"
        description = f"Test action {action_id}"
        super().__init__(name=name, description=description, *args, **kwargs)
        self.action_id = action_id

    def execute(self, state: CalibrationStateModel, payload: Optional[FormModel] = None):
        # Initialize counters if they don't exist
        state.measured = state.measured or defaultdict(lambda: {"counter": 0})

        # Increment counter for this action
        counter = state.measured.get("counter", 0)
        state.measured["counter"] = counter + 1

        # Store the last action ID for verification
        state.measured["last_action_id"] = self.action_id

        return state


class TestProcedure(CalibrationProcedure):
    """A test procedure that adds a specified number of simple actions."""

    def __init__(self, num_actions: int, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Create and add actions
        for i in range(num_actions):
            action = SimpleAction(action_id=i, hardware=self.hardware)
            self.add_action(action)


class MockHardware:
    """Mock hardware for testing."""

    def __init__(self):
        self.calibrator = type(
            "MockCalibrator",
            (),
            {
                "procedure_file": "mock_procedure.yml",
                "calibration_file": "mock_calibration.yml",
                "calibration_data": None,
            },
        )


def test_procedure_undo_performance():
    """Test that undo operations are performant with a large number of actions."""
    # Constants
    NUM_ACTIONS = 100
    TIME_LIMIT_SECONDS = 1

    # Setup
    mock_hardware = MockHardware()
    procedure = TestProcedure(num_actions=NUM_ACTIONS, hardware=mock_hardware)

    # Get all actions
    actions = procedure.get_actions()
    assert len(actions) == NUM_ACTIONS

    # Start timing
    start_time = time.time()

    # Dispatch all actions one by one
    for i, action in enumerate(actions):
        state = procedure.dispatch(action, {})

        # Verify state is correct after each dispatch
        assert state.measured["counter"] == i + 1
        assert state.measured["last_action_id"] == i
        assert len(state.completed_actions) == i + 1
        assert action.name in state.completed_actions

    # Verify all actions were applied
    assert procedure.state.measured["counter"] == NUM_ACTIONS
    assert len(procedure.state.completed_actions) == NUM_ACTIONS

    # Undo all actions one by one
    for i in range(NUM_ACTIONS):
        state = procedure.undo()

        # Verify state is correct after each undo
        expected_counter = NUM_ACTIONS - i - 1
        if expected_counter > 0:
            assert state.measured["counter"] == expected_counter
            assert state.measured["last_action_id"] == expected_counter - 1

        assert len(state.completed_actions) == NUM_ACTIONS - i - 1

    # Verify all actions were undone
    assert procedure.state.measured.get("counter", 0) == 0
    assert len(procedure.state.completed_actions) == 0

    # Calculate total time and assert it's within limit
    total_time = time.time() - start_time
    print(f"Total time for {NUM_ACTIONS} dispatch+undo operations: {total_time:.2f} seconds")

    # Assert that the whole test runs in less than the time limit
    assert total_time < TIME_LIMIT_SECONDS, f"Test exceeded time limit of {TIME_LIMIT_SECONDS} seconds"
