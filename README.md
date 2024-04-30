# SSEC-JHU evolver-ng

[![CI](https://github.com/ssec-jhu/evolver-ng/actions/workflows/ci.yml/badge.svg)](https://github.com/ssec-jhu/evolver-ng/actions/workflows/ci.yml)
<!---[![Documentation Status](https://readthedocs.org/projects/ssec-jhu-evolver-ng/badge/?version=latest)](https://ssec-jhu-evolver-ng.readthedocs.io/en/latest/?badge=latest) --->
<!---[![codecov](https://codecov.io/gh/ssec-jhu/evolver-ng/branch/main/graph/badge.svg?token=0KPNKHRC2V)](https://codecov.io/gh/ssec-jhu/evolver-ng) --->
[![Security](https://github.com/ssec-jhu/evolver-ng/actions/workflows/security.yml/badge.svg)](https://github.com/ssec-jhu/evolver-ng/actions/workflows/security.yml)
<!---[![DOI](https://zenodo.org/badge/<insert_ID_number>.svg)](https://zenodo.org/badge/latestdoi/<insert_ID_number>) --->


![SSEC-JHU Logo](docs/_static/SSEC_logo_horiz_blue_1152x263.png)

# About

The next generation of software control for eVolver. This package provides a modular bioreactor controller framework and
REST api focused on extensibility in hardware and experiment control. The REST api enables decoupling of the core
control from the user interaction and aims to enable support for configuration of new hardware without explicit UI
componentry being required.

References:
* eVolver wiki: https://khalil-lab.gitbook.io/evolver
* original code base: https://github.com/FYNCH-BIO


🚧 ❗ This project is under active early development - some of the information below may be out of date ❗ 🚧


# Extensibility

The system is designed to be easily extensible both by a user operating a box under their desired experimental
conditions, and also by a hardware developer needing a software driver for their on-chip sensors. All extension points
will be easily shareable via pip installations or by sharing configuration files.

❗❗ NOTE: The information in this section does not represent instructions, but rather design goals. We will update with
real instructions when the necessary hook-ups have been added to make use of these goals. To test and run an example app
see Build instructions below ❗❗

## Configuration

### Config file

Configuration of the eVolver system including provisioned hardware and experiments can be expressed in a single yaml
file, for example:

```yaml
enable_react: true  # run the experiment controllers
enable_commit: true  # enable controllers to send commands to hardware
interval: 20  # how often in seconds to loop
hardware:
  temp:
    driver: evolver.hardware.default.TempSensorDriver
  od90:
    driver: evolver.hardware.default.OD90SensorDriver
    config:
      key: val
  pump:
    driver: evolver.hardware.default.PumpEffectorDriver
controllers:
- driver: evolver.controllers.default.ChemostatExperimentController
  config:
    start_od: 0
    start_time: 0
```

This enables both sharing of the eVolver setup and experiment with others, and also the ability to easily resume the
experiment on hardware failure.

### Web api

The web api will expose all configuration options also available in the config file so configuration can be done in a
user-friendly manner via a web browser.

## Experiment control

In the default mode, the eVolver application will run a loop every 20 seconds which:

* **reads** the sensor values into a device object which can later be read from
* **evaluates** the experiment controllers in order. The code in the controllers can access sensor data and set effector
  values.
* **progresses** the experiment by sending the updates from controllers to the underlying hardware device (e.g. set pump
  flow rate or start stirring)


### Hardware device extensions

Once an on-board device is created and attached to the serial bus, a new hardware driver can be created by implementing
the `get`, `set`, `read` and/or `commit` methods of a hardware driver. For example (not real code, interface subject to
change):


```py
class MyNewHardware(Sensor):
    def read(self):
      # send the serial command specific for this device, which can handle
      # the particular output it creates
      data = self.evolver.serial.communicate(SerialData(self.addr, data_bytes, kind='r'))
      self.loaded_data = self.convert_serial(data)

    def get(self):
      return Output(self.loaded_data)  # output converted from raw serial to real data
```

### Experiment controller extensions

Experiment controllers simply need to implement the control method, which will be called in the **evaluate** phase
mentioned above. These can read values from the eVolver devices and set commands to others for changing the
environment. A simple example might look like (not real code, interface subject to change):


```py
class MyCoolExperiment(Controller):
   class Config(VialConfigBaseModel):
      od_sensor: str = 'OD90'
      flow_rate_factor: int = 10

   def control(self):
      # read values from a particular sensor
      od90 = self.evolver.get(self.config.od_sensor)
      # set an effector based on this value
      pump_flow_rate = od90 / self.config.flow_rate_factor
      self.evolver.set('PUMP', pump_flow_rate)
```

There will also likely be a generic "development" controller that can take a blob of python code to execute, so for
example a user can write code in the webUI which will get evaluated during each loop. This will enable rapid
development, while also making it simple to "freeze" that code into a module (that can be committed and shared more
easily) since the body can simply be copied to Controller classes `control` method as above!

# Installation, Build, & Run instructions

### Prerequisite

Build, testing and examples use the tox utility to set up virtual environments, the only perquisite on the development
system is python and tox (represented in `requirements/dev.txt`):

```
pip install -r requirements/dev.txt
```

### Test

Run tox within the repo base path to run an end-to-end test and packaging:

```
tox
```

or to run just the unit tests (for example):

```
tox -e test
```

### Example run

We can leverage the tox testing environment, which contains all required dependencies, to run the application locally
for evaluation:

```
tox -e test exec -- python -m evolver.app.main
```

You should then be able to visit the automatically generated API documentation in your local browser at
https://localhost:8000/docs (or https://localhost:8000/redoc). From there you can experiment with sending
data and reading from various endpoints (which will eventually be hooked up to a web user interface).
