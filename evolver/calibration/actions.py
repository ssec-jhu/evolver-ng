class DisplayInstructionAction:
    def __init__(self, description, name):
        self.description = description
        self.name = name

    def execute(self, state, action):
        new_state = state.copy()
        return new_state


class VialTempReferenceValueAction:
    def __init__(self, hardware, description: str, vial_idx: int, name: str):
        self.hardware = hardware
        self.description = description
        self.vial_idx = vial_idx
        self.name = name

    def execute(self, state, action):
        # Validate action
        if "reference_value" not in action:
            raise ValueError("Action must include 'reference_value'")

        reference_value = action["reference_value"]

        # Update state immutably
        new_state = state.copy()
        vial_key = f"vial_{self.vial_idx}"

        if self.hardware.name not in new_state:
            new_state[self.hardware.name] = {}

        if vial_key not in new_state[self.hardware.name]:
            new_state[self.hardware.name][vial_key] = {"reference": [], "raw": []}

        new_state[self.hardware.name][vial_key]["reference"].append(reference_value)
        return new_state


class VialTempRawVoltageAction:
    def __init__(self, hardware, vial_idx: int, description, name):
        self.name = name
        self.hardware = hardware
        self.description = description
        self.vial_idx = vial_idx

    def execute(self, state, action):
        # This step doesn't require any action input
        # Read sensor value from hardware
        # TODO: Find out how to read vial sensor value from hardware

        # beware the serial read has latency associated with it, e.g. 1.5s... and the best way is to do read once  (goes to buffer) and get on that.
        # so think about hoisting all reads to the procedure state, periodically update it.
        sensor_value = self.hardware.read()[self.vial_idx]

        # sensor_value = 0.666

        # Update state immutably
        new_state = state.copy()
        hardware_name = self.hardware.name
        vial_key = f"vial_{self.vial_idx}"

        # Initialize hardware section in state if necessary
        if hardware_name not in new_state:
            new_state[hardware_name] = {}

        # Initialize vial data in state if necessary
        if vial_key not in new_state[hardware_name]:
            new_state[hardware_name][vial_key] = {"reference": [], "raw": []}

        new_state[hardware_name][vial_key]["raw"].append(sensor_value)
        return new_state


class VialTempCalculateFitAction:
    def __init__(self, hardware, vial_idx: int, description: str, name: str):
        self.hardware = hardware
        self.description = description
        self.name = name
        self.vial_idx = vial_idx

    def execute(self, state, action):
        hardware_name = self.hardware.name
        vial_key = f"vial_{self.vial_idx}"

        # Ensure that the necessary data is available in the state
        if hardware_name not in state or vial_key not in state[hardware_name]:
            raise ValueError(f"No data available for {hardware_name} {vial_key}")

        vial_data = state[hardware_name][vial_key]
        reference_values = vial_data.get("reference", [])
        raw_values = vial_data.get("raw", [])

        if not reference_values or not raw_values:
            raise ValueError(f"Insufficient data to calculate fit for {hardware_name} {vial_key}")

        # Perform the fit calculation
        # TODO: Findout how to call the fit calculation method from the hardware
        # fit_parameters = self.hardware.calibrate_transformer.calculate_fit(reference_values, raw_values)
        fit_parameters = [0.5, 0.5]

        # Update state immutably with fit parameters
        new_state = state.copy()
        new_state[hardware_name][vial_key]["fit_parameters"] = fit_parameters

        return new_state
