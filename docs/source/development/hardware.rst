Developing custom hardware drivers
==================================

Basics
------

Implementing hardware within the eVolver system means creating a new subclass of
the appropriate driver interface classes, creating concrete implementations of
the abstract methods therein.

For sensors::

    class MySensorDriver(SensorDriver):
        class Config(SensorDriver.Config):
            addr: str

        # model for output data
        class Output(SensorDriver.Output):
            raw: int
            value: float | None

        def read(self):
            # Read the hardware here, set and return self.outputs
            self.outputs = ...
            return self.outputs

For effectors::

    class MyEffectorDriver(EffectorDriver):
        class Config(EffectorDriver.Config):
            addr: str

        # model for input data
        class Input(EffectorDriver.Input):
            value: float | None
            raw: int | None

        def commit(self, value):
            # Apply the values from self.proposal to the underlying hardware by
            # applicable means. This should set committed to the values applied.
            apply_values_to_hardware(self.proposal)
            self.committed = self.proposal

A combined driver can be created by creating a sublcass of both.

As with all components in the system, the drivers contain a Config class which
is used in creating an instance within the application from whatever
configuration source is used (for example the YAML file or web API). See
:ref:`config` for more information on Config objects, creation and their usage.

Using the built-in serial interface
-----------------------------------

Many drivers will want to use the shared serial bus attached to a standard
eVolver setup, addressing a specific component on that line. Since this is a
shared global resource that must be locked to avoid contention, it is defined at
the main eVolver level. When the eVolver manager constructs hardware drivers, it
passes itself in as the `evolver` attribute to the driver constructor, in a
manner similar to::

    self.hardware[driver.name] = driver.class(self, **driver.config)

In the driver code, then, the serial interface can be accessed as follows::

    def read(self):
        with self.evolver.serial as serial:
            response = serial.communicate(SerialData(self.addr, data)))

The locking, data formatting and serial protocol details are all handled within
the serial module. See :py:class:`SerialData<evolver.serial.SerialData>` for
information on how to create the data object to send to the serial interface.

Input/Output
------------

Similar to `Config`, hardware classes also define an `Input` (for effectors) and
`Output` (for sensors). The classes should contain a model for the data read
from  and transformed or transformed and sent to hardware.

The use of model classes here, as in `Config`, provides a schema for use in
input and display by clients, documentation, and validation of data. Validation
implies that the model defined must define all useful types of each field,
exceptions will occur and be expected for cases where bad input is given.

.. note::
    The physical value (subject to calibration transformation) represented in an
    `Output` class should in general be defined to be optional (e.g. `float | None`)
    to allow for cases where a calibrator is unspecified - for example prior to
    running a calibration procedure. The `None` value communicates to consumers that
    calibration is not available or has failed. In other cases, a fallback value
    must be used when performing the transformation (`_transform`) when constructing
    the `Output` object in the driver. See below for more details on calibration
    transformations.


Calibrated value transformations
--------------------------------

If your hardware component requires calibration, the raw voltages read from the
sensor should be transformed into physical units by the calibrators
transformers. The hardware base class provides a convenience method to apply
these transformations using the calibrator configured on it, which dispatch to
transformation functions and do error handling, logging and fallback as needed.

In hardware driver code, we use the following for transforming raw outputs from
a sensor::

    raw_voltage = int(serial_response[vial])
    calibrated_value = self._transform('output_transformer', 'convert_from', raw_voltage, vial)

And for transforming inputs to be sent to an effector::

    real_value = self.proposal[vial].value
    raw_setting = self._transform('input_transformer', 'convert_to', real_value, vial)

The transform function will fallback to a null value (`None`) when either the
transformer does not exist (in the case that the user has not attached a
calibrator or it does not have calibration data) or if errors occur in the
transformation.

A null value should be allowed by the `Input` and `Output` models for calibrated
values and indicates that the calibration is not available or has failed. In
cases where a value other than null is appropriate, the transform function has a
`fallback` parameter which can be used to provide a default value::

    self._transform('output_transformer', 'convert_from', raw_voltage, vial, fallback=0)

This section discussed making the calibration conversion within hardware code,
for more information on calibrators, their transformers and calibration
procedures, please see the :doc:`calibrators` documentation.

Testing
-------

This package provides a test suite framework for testing hardware drivers backed
by the serial interface. The test suite is parameterized by:

* Configuration applied to the driver
* Inputs to the driver for effectors, or Outputs expected from sensors
* A set of simulated serial responses for sensors, or expected serial commands
  issue for effectors.

The test suites can be used by parametrizing a subclass implementation of either
of `SerialVialSensorHardwareTestSuite` or `SerialVialEffectorHardwareTestSuite`
classes. See the tests in `evolver/hardware/standard/tests` for examples.


