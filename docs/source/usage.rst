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

The eVolver server is self-contained and described by a static configuration
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

Since the hardware portion of the eVolver is directly related to the physical
setup of the evolver box, configuration should often be obtained from the source
of the hardware or from examples for modular hardware components shared by their
creators. The evolver-ng package will contain such examples for hardware
components built or maintained by the eVolver team.

As with all configuration in the system, each component will have a class
specifying the code component that controls it, along with a configuration
section for user settings. For example, the OD90 sensor might be configured as::

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

Configure experiments
=====================

Monitoring and starting/stopping experiments
============================================

Aborting
========

