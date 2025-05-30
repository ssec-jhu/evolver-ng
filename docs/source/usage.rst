Usage
=====

As a user of eVolver, you will primarily perform the following functions through
either the web interface or via the http API:

* Configure your hardware setup by configuring the hardware drivers and
  parameters matching your physical setup.
* Run calibration procedures to create mappings of raw sensor values to physical
  units, or apply existing ones to the hardware.
* Configure your experiments by setting parameters on existing available
  controller logic. If you are developing new controller logic, see
  :doc:`development/controllers` for details writing and installation.
* Start, stop and monitor the progress of your experiments.

Applying configuration
-----------------------

The eVOLVER server is self-contained and described by a static configuration
containing the physical setup and experiment control logic. This allows it to
run experiments without intervention for long periods of time, and withstand
failure and restarts, losing only the down-time interval.

Configuration in the UI can be done by selecting a device in the "device" menu
and then selecting the "configure" tab. You can edit individual configuration
fields or upload a new configuration file.

Via the web API, JSON configuration can be uploaded using a POST request::

    curl -XPOST -Hcontent-type:application/json -F "file=@/path/to/config.json" http://<evolver-ip>:8080/

Likewise it can be downloaded for editing and re-upload using a GET request::

    curl -XGET http://<evolver-ip>:8080/ > /path/to/config.json

Configuring the hardware
-------------------------

Since the hardware portion of the eVOLVER is directly related to the physical
setup of the eVOLVER box, configuration should often be obtained from the source
of the hardware or from examples for modular hardware components shared by their
creators. The evolver-ng package will contain such examples for hardware
components built or maintained by the eVOLVER team.

As with all configuration in the system, each component will have a class
specifying the code component that controls it, along with a configuration
section for user settings. For example, the OD90 sensor might be configured as:

.. code-block:: yaml

    hardware:
      OD90:
        classinfo: evolver.hardware.standard.od_sensor.ODSensor
        config:
          addr: "od90"
          integrations: 500

For provided components, see the respective documentation for the details and
appropriate values of such components. The :meth:`<evolver.app.main.get_schema>`
API can also be used to get the expected config schema and often will provide a
description of each field in the result.

For custom hardware, follow the :doc:`development/hardware` guide to create an
appropriate driver, and then configure as above, providing the classinfo for
your custom driver.

Calibration
===========

Each hardware component can have attached to it a
:py:class:`Calibrator<evolver.calibration.interface.Calibrator>`, which is both
used to transform raw sensor values into their respective physical units (via a
:py:class:`Transformers<evolver.calibration.interface.Transformer>`), and to
perform the procedure which results in the data necessary to configure these
transformers.

As a user, you will primarily be interacting with the calibration via either
configuring the calibrator with desired behavior via configuration parameters
(see above), and/or running a procedure via the web interface.

The calibration system is designed to be self-described, enabling developers to
add procedures with no requirement to modify the core system. Procedures will
proceed with the following flow, where at each step instructions and required
user inputs will be provided:

* Select a file to save the calibration state to during the procedure. This is
  configured on the calibrator via the `procedure_file` parameter.
* Start or resume the procedure. Via the UI select the "hardware" tab, find the
  desired hardware and click on the "calibrate" button, then select "start" or
  "resume" as appropriate.
* Follow each step (action) and input data as required.
* Save the procedure. This writes the calibration state to the file specified
  in the first step.
* Apply the calibration. When the procedure is complete, we can apply it by
  setting the `calibration_file` parameter on the calibrator to the
  `procedure_file`.

For more information on the calibration system, see the :doc:`development/calibrators`

Configure experiments
=====================

Experiments are configured in the same manner as other components in the system,
such as hardware described above. The eVOLVER has a set of named experiments,
which in turn are made up of one or more
:py:class:`Controllers<evolver.controller.interface.Controller>`. Each
controller is a descriptor object that has a config section, for example:

.. code-block:: yaml

    experiments:
      growth:
        enabled: true
        controllers:
        - classinfo: evolver.controller.standard.growth.GrowthController
          config:
            target: 0.5
            duration: 3600
            interval: 60

Where "growth" as a key in the above refers to the name of the experiment within
the system.

Monitoring and starting/stopping experiments
============================================

During the lifetime of an experiment run, users can monitor all activities and
hardware readouts via the built-in history server. The server records data on
a per-vial level (as applicable) with the following properties:

* **Kind**: The kind of recording, one of:
   * "sensor": A sensor reading.
   * "log": A log message that is otherwise not categorized as an "event".
   * "event": An event, such as a calibration or experiment start/stop, or
     arbitrary events emitted by controllers. Events are a special case of a log
     message for use in e.g. drawing lines on graphs.
* **Name**: The name of the entity, such as the hardware name for a sensor type or
  the controller for an event. This is a discriminator for each entity within
  the system.
* **Vial**: The vial number, if applicable.
* **Time**: The time of the recording.
* **Data**: Recorded data, as a JSON object.

History is visible in several places in the UI, including in the sensor plots
under the "hardware" tab (included event data as vertical lines), and in the log
interfaces, for example in the "experiment" tab, in addition to error messages
surfaced.

See the web api `/history` endpoint for details on query parameters and returned
data.

Aborting
========

In general, once started, the eVOLVER will continuously run the experiment loop
(see :ref:`experiment_loop`) until stopped. When there are experiments
configured on the system, this means that physical actuation of some devices on
the system may be carried out, and in cases where feedback about certain
conditions in the environment (for example, the liquid volume in a vial),
unintended physical conditions may ensue.

In such a case, there is a global abort endpoint that can be used to immediately
stop all control activity regardless of experiment. In the UI this button is
available in all contexts, and via the API it can be accessed via a POST request
to `/abort`.

.. note::
  In all cases this will issue a stop to all hardware configured on the system,
  however note that this may not result termination of the electric supply to
  any hardware. Failure in communication to a hardware during abort may result
  in failure to mitigate physical conditions.

There is a `/start` endpoint to reverse the effect of `/abort`.