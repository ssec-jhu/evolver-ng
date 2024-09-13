from fastapi import FastAPI, HTTPException
from typing import Dict, List
from pydantic import BaseModel

app = FastAPI()

# Store calibration procedures by session ID
# TODO: Explore persistent storage options, so calibration procedures can be resumed after server restarts
# TODO: procedure resumption.

calibration_sessions: Dict[str, "CalibrationProcedure"] = {}

# Assume sensor_manager is already initialized and populated with sensors
sensor_manager = SensorManager()


class StartCalibrationRequest(BaseModel):
    sensor_ids: List[str]


@app.post("/calibration/{session_id}/start")
async def start_calibration(session_id: str, request: StartCalibrationRequest):
    # Initialize sensors
    sensors = sensor_manager.select_sensors_for_calibration(request.sensor_ids)

    # Create calibration procedure with session ID
    procedure = CalibrationProcedure( sensors=sensors, session_id=session_id)

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
    calibration_sessions[session_id] = procedure

    # Start the procedure
    await procedure.run()
    return {"status": "Calibration started."}


@app.post("/calibration/{session_id}/acknowledge-global-instruction")
async def acknowledge_global_instruction(session_id: str):
    procedure = calibration_sessions.get(session_id)
    if procedure:
        current_step = procedure.steps[procedure.current_step_index]
        if isinstance(current_step, InstructionGlobalStep):
            current_step.mark_instruction_complete()
            await procedure.run()
            return {"status": "Global instruction acknowledged and procedure resumed."}
        else:
            raise HTTPException(status_code=400, detail="Current step is not a global instruction step.")
    else:
        raise HTTPException(status_code=404, detail="Calibration session not found.")


@app.post("/calibration/{session_id}/sensor/{sensor_id}/acknowledge-instruction")
async def acknowledge_sensor_instruction(session_id: str, sensor_id: str):
    procedure = calibration_sessions.get(session_id)
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
        raise HTTPException(status_code=404, detail="Calibration session not found.")


class ReferenceValueRequest(BaseModel):
    value: float


@app.post("/calibration/{session_id}/sensor/{sensor_id}/input-reference")
async def input_reference_value(session_id: str, sensor_id: str, request: ReferenceValueRequest):
    procedure = calibration_sessions.get(session_id)
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
        raise HTTPException(status_code=404, detail="Calibration session not found."}
