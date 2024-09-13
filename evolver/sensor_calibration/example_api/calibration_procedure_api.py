from fastapi import FastAPI, HTTPException
from typing import Dict, List
from pydantic import BaseModel

app = FastAPI()

# Notes:
# TODO: If ui needs more info on valid inputs for current step, expand Step class a la acknowledge_url. I can imagine for example including  min/max values for input, number of inputs etc...
# TODO: Current step index isn't perfect, it doesn't account for SensorStep steps, a SensorStep = 1 step for each sensor in self.sensors


# Store calibration procedures by calibration name
# TODO: Explore persistent storage options, so calibration procedures can be resumed after server restarts
calibration_procedures: Dict[str, "CalibrationProcedure"] = {}

# Assume sensor_manager is already initialized and populated with sensors
sensor_manager = SensorManager()


class StartCalibrationRequest(BaseModel):
    sensor_ids: List[str]

@app.get("/calibration/{calibration_name}/current-step", response_model=CurrentStepResponse)
async def get_current_step(calibration_name: str):
    procedure = calibration_procedures.get(calibration_name)
    if not procedure:
        raise HTTPException(status_code=404, detail="Calibration with that name was not found.")
    
    current_step = procedure.steps[procedure.current_step_index]
    
    # Determine the acknowledge URL by calling the method on the step
    if isinstance(current_step, InstructionSensorStep):
        # Example: Provide a specific sensor ID, possibly the first sensor for now (adjust as needed)
        acknowledge_url = current_step.acknowledge_url(calibration_name, procedure.sensors[0].id)
    else:
        acknowledge_url = current_step.acknowledge_url(calibration_name)
    
    return {
        "step_name": current_step.name,
        "instructions": current_step.instructions,
        "input_required": current_step.input_required,
        "acknowledge_url": acknowledge_url
    }


@app.post("/calibration/{calibration_name}/start")
async def start_calibration(calibration_name: str, request: StartCalibrationRequest):
    # Initialize sensors
    sensors = sensor_manager.select_sensors_for_calibration(request.sensor_ids)

    # Create calibration procedure with a name
    procedure = CalibrationProcedure(sensors=sensors, calibration_name=calibration_name)

    # Example of a calibration procedure for temperature sensors
    # Add global instructions
    procedure.add_step(InstructionGlobalStep("Ensure all sensors are connected and click 'Next'."))
    procedure.add_step(InstructionGlobalStep("Fill sensors with 15ml water each and click 'Next'."))

    # Add sensor-specific calibration steps (e.g., collect 3 calibration points)
    for i in range(3):  # Adjust the range for the desired number of calibration points
        # Add sensor instruction step
        set_temp = (i+1)*10+10  # Example: 20, 30, 40
        # Note: GlobalStep only runs once
        # TODO: a step with a "done condition" that evaluates every second. In this case it could read the voltage from all sensors and wait until they are stabilized.
        procedure.add_step(InstructionGlobalStep(
            instructions_template=f"Set Evolver temp control to {set_temp} setting and wait for equilibrium (consistent onboard readings), and click 'Next'."
        ))
        # Note: A SensorStep will run once for each selected sensor.
        procedure.add_step(InstructionSensorStep(
            instructions_template=f"Calibration Point for {set_temp}: Place thermometer into {{sensor_id}}, and click 'Next'."
        ))
        # Add step to input reference value
        procedure.add_step(InputReferenceValueStep(reference_type="temperature"))
        # Add step to read sensor data
        procedure.add_step(ReadSensorDataStep())

    # Final global step to calculate the fit model after collecting all calibration points
    procedure.add_step(CalculateFitGlobalStep())

    # Store the procedure
    calibration_procedures[calibration_name] = procedure

    # Start the procedure
    await procedure.run()
    return {"status": "Calibration started."}


@app.post("/calibration/{calibration_name}/acknowledge-global-instruction")
async def acknowledge_global_instruction(calibration_name: str):
    procedure = calibration_procedures.get(calibration_name)
    if procedure:
        current_step = procedure.steps[procedure.current_step_index]
        if isinstance(current_step, InstructionGlobalStep):
            current_step.mark_instruction_complete()
            await procedure.run()
            return {"status": "Global instruction acknowledged and procedure resumed."}
        else:
            raise HTTPException(status_code=400, detail="Current step is not a global instruction step.")
    else:
        raise HTTPException(status_code=404, detail="Calibration procedure with that name was not found.")


@app.post("/calibration/{calibration_name}/sensor/{sensor_id}/acknowledge-instruction")
async def acknowledge_sensor_instruction(calibration_name: str, sensor_id: str):
    procedure = calibration_procedures.get(calibration_name)
    if procedure:
        sensor = sensor_manager.get_sensor(sensor_id)
        if not sensor:
            raise HTTPException(status_code=404, detail=f"Sensor {sensor_id} not found.")
        current_step = procedure.steps[procedure.current_step_index]
        if isinstance(current_step, InstructionSensorStep):
            current_step.mark_instruction_complete(sensor_id)
            if all(current_step.is_complete(s.id) for s in procedure.sensors):
                await procedure.run()
            return {"status": f"Instruction for sensor {sensor_id} acknowledged."}
        else:
            raise HTTPException(status_code=400, detail="Current step is not a sensor instruction step.")
    else:
        raise HTTPException(status_code=404, detail="Calibration with that name was not found.")


class ReferenceValueRequest(BaseModel):
    value: float


@app.post("/calibration/{calibration_name}/sensor/{sensor_id}/input-reference")
async def input_reference_value(calibration_name: str, sensor_id: str, request: ReferenceValueRequest):
    procedure = calibration_procedures.get(calibration_name)
    if procedure:
        sensor = sensor_manager.get_sensor(sensor_id)
        if not sensor:
            raise HTTPException(status_code=404, detail=f"Sensor {sensor_id} not found.")
        current_step = procedure.steps[procedure.current_step_index]
        if isinstance(current_step, InputReferenceValueStep):
            current_step.set_reference_value(sensor_id, request.value)
            if all(current_step.is_complete(s.id) for s in procedure.sensors):
                await procedure.run()
            return {"status": f"Reference value for sensor {sensor_id} received and procedure resumed."}
        else:
            raise HTTPException(status_code=400, detail="Current step is not expecting input.")
    else:
        raise HTTPException(status_code=404, detail="Calibration with that name was not found."}
