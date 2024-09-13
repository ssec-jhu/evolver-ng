class CalibrationProcedure:
    def __init__(self, sensors, session_id: str):
        """
        Initialize the CalibrationProcedure with a sensor type, selected sensors, and a session ID.

        :param sensors: List of sensors involved in the calibration procedure.
        :param session_id: Unique identifier for the calibration session.
        """
        self.sensors = sensors  # List of Sensor objects
        self.session_id = session_id  # Unique session ID
        self.steps = []  # List to hold the sequence of calibration steps
        self.current_step_index = 0  # Track the current step index
        self.context = {
            "sensors": sensors,
            "procedure": self,  # Add self to context for access in steps
        }
        # Store calibration data per sensor within the procedure
        self.session_calibration_data = {sensor.id: CalibrationData() for sensor in sensors}
        self.lock = asyncio.Lock()  # For thread safety

    def add_step(self, step: CalibrationStep):
        """
        Add a calibration step to the procedure.

        :param step: A CalibrationStep object to be added to the procedure.
        """
        self.steps.append(step)

    async def execute_step(self):
        """
        Execute the current calibration step, handling global and sensor-specific steps.
        """
        async with self.lock:
            if self.current_step_index < len(self.steps):
                step = self.steps[self.current_step_index]
                print(f"Executing step: {step.name}")

                if isinstance(step, GlobalCalibrationStep):
                    # Execute global step
                    await step.action(context=self.context)
                    if step.is_complete():
                        self.current_step_index += 1
                elif isinstance(step, SensorCalibrationStep):
                    # Execute sensor-specific step
                    for sensor in self.sensors:
                        if not step.is_complete(sensor.id):
                            await step.action(sensor, context=self.context)
                    # Move to next step if all sensors have completed the step
                    if all(step.is_complete(sensor.id) for sensor in self.sensors):
                        self.current_step_index += 1
                else:
                    # Handle other types of steps if any
                    pass
            else:
                print("All steps completed.")

    def is_complete(self) -> bool:
        """
        Check if all steps in the procedure have been completed.

        :return: True if all steps are completed, otherwise False.
        """
        return self.current_step_index >= len(self.steps)

    async def run(self):
        """
        Run all the calibration steps in sequence.
        """
        while not self.is_complete():
            await self.execute_step()
            # Since we can't block, we break here and rely on external triggers to resume
            break  # Execution will resume upon external events (e.g., user input)
