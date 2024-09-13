Sensor Calibration 1 pager.

### Scope: 
Make collecting data required to accurately calibrate sensors customizable using a convenient api and to handle the collection of that data.

### Demo:
From a high level this is what a temperature calibration procedure looks like. OD calibration can be represented too, I'll have a shot at that shortly.
https://github.com/ssec-jhu/evolver-ng/blob/iainland/calibration-system/evolver/sensor_calibration/example_api/calibration_procedure_api.py#L51-L78

### Detailed description:

The core of this system is a datastructure, called `CalibrationData` that pairs reference values with raw values, e.g. Actual temp measured in a vial and the voltage for that vial's temp sensor. These pairs are fed into function that calculates, linear fit, the result of this calculation is also included in the data structure. Since `CalibrationData` stores data points as a dict, whatever any kind of data required to calibrate a sensor can be put there.

For illustrative purposes we're focussed on the simplest use case of calibrating temperature sensors. In this case pairings of reference value to raw value is all that is required to calculate a usable fit.

A `SensorManager` maps `CalibrationData`  to an individual `Sensor` for example the temp sensor on vial 1 may have id: `temp_sensor_1`. It's anticipated that all sensors attached to the device are registered with the manager when it initializes.

`CalibrationStep` handles building the `CalibrationData` structure.

Towards this end a `CalibrationStep` will typically do one of 3 things.

- set a reference data point in calibration data (e.g. real world temp reading taken using a thermometer by the user)
https://github.com/ssec-jhu/evolver-ng/blob/iainland/calibration-system/evolver/sensor_calibration/calibration_step.py#L229

- sets the raw value data point in calibration data (e.g. raw voltage reading from the sensor)
https://github.com/ssec-jhu/evolver-ng/blob/iainland/calibration-system/evolver/sensor_calibration/calibration_step.py#L199

- instruct the user to take some action
https://github.com/ssec-jhu/evolver-ng/blob/iainland/calibration-system/evolver/sensor_calibration/calibration_step.py#L161

a `CalibrationStep`'s behavior is first  distinguished by the Class it inherits from.

`GlobalCalibrationStep` will not loop over selected sensors, they'll execute once for the `CalibrationProcedure`.

`SensorCalibrationStep` will loop over selected sensors, executing that step once for each selected sensor.

`CalibrationProcedure` is used to coordinate and organize the steps into a cohesive procedure that is complete when all constituent steps are complete. It provides shared state as necessary between steps, manages procedure state like the overall procedure progress and provides async features to enable non-blocking procedures. The CalibrationProcedure can be enhanced to support resumable/recoverable calibration procedures, especially with the named and persisted procedure concept introduced in this proposal.

Upon completion a `CalibrationProcedure` should save the `CalibrationData` it has been collating to the respective `Sensors` in the `SensorManager`

At that point the `SensorManager` is able to provide the broader framework with calibration data for the sensors.

### Caveats:
 
None of this has been run or tested. I wanted to make sure all the requirements of the existing calibration procedures could be covered with this system with enhancements like a simple API and resumable procedures. I think all requirements can be accomodated. If everyone approves of this approach I can spend the time to stand up a running demo.

As you read through this, there are areas that are not consistent or don't fully work.
For example I haven't written the logic to unwrap steps that iterate over sensors, to give a complete count of steps in a procedure. The CalibrationData structure doesn't enforce 1:1 mapping of reference to raw values.

Ignore that level of detail if you can.

In putting this together, to make the manageable, i've also ignored the existing framework, i'm sure it can provide some features like those provided by the SensorManager in this example. I've just ignored it pending approval / discussion of this proposal. Similarly this design is not integrated with the existing api, there's a reference api in the example_api directory, that should be not too hard to integrate with what's already available.

I've also ignored the existing calibration features, my understanding is they mostly pertain to linear fits, and other fits the user might put together. The scope of this work isn't to touch any of that, though it ought to provide an interface that makes integrating with that possible.