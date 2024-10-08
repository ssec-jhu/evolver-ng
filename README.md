# SSEC-JHU evolver-ng

[![CI](https://github.com/ssec-jhu/evolver-ng/actions/workflows/ci.yml/badge.svg)](https://github.com/ssec-jhu/evolver-ng/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/ssec-jhu/evolver-ng/graph/badge.svg?token=mkRet8Fep0)](https://codecov.io/gh/ssec-jhu/evolver-ng)
[![Security](https://github.com/ssec-jhu/evolver-ng/actions/workflows/security.yml/badge.svg)](https://github.com/ssec-jhu/evolver-ng/actions/workflows/security.yml)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.12532759.svg)](https://doi.org/10.5281/zenodo.12532759)
[![Documentation Status](https://readthedocs.org/projects/evolver-ng/badge/?version=latest)](https://evolver-ng.readthedocs.io/en/latest)

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

Configuration of the eVolver system including provisioned hardware and experiments must be expressed in a single yaml.

By default the config file is named `evolver.yml` and is stored in the project root directory file. This filename and path is determined by [`evolver.settings.AppSettings.CONFIG_FILE`](https://github.com/ssec-jhu/evolver-ng/blob/main/evolver/settings.py) and can be customized.

for example:

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

#### Bootstrapping the `evolver.yml` config file

By default `evolver-ng` requires an `evolver.yml` (file name can be configured at [`settings.app_settings.CONFIG_FILE`](https://github.com/ssec-jhu/evolver-ng/blob/main/evolver/settings.py)) file to exist in the project's root directory for it to start.

However, sometimes you want to start `evolver-ng` before `evolver.yml` exists. For example the very first time you run the app.

For this reason there is an escape hatch that allows `evolver-ng` to start without `evolver.yml` using the following environment variable.

`EVOLVER_LOAD_FROM_CONFIG_ON_STARTUP=false`

For example, if you run `evolver-ng` for local development or testing, without `evolver.yml` existing you must pass this flag:

```shellscript
EVOLVER_LOAD_FROM_CONFIG_ON_STARTUP=false tox -e test exec -- python -m evolver.app.main
```

##### Creating a valid config file

There are a few distinct ways to create a valid evolver config.

- If you passed the `EVOLVER_LOAD_FROM_CONFIG_ON_STARTUP=false` flag. The evolver will be given an in-memory config with default values. The `/` endpoint will available on the evolver-ng HTTP API, this endpoint accepts POST requests with a config payload, if you attempt to submit an invalid config to this endpoint it will respond with detailed validation errors. If you submit a valid config to the `/` endpoint the `evolver.yml` file will be created so the flag needn't be passed the next time you run the app. The [`evolver-ui`](https://github.com/ssec-jhu/evolver-ui) package provides a webapp that can be used to interact with the `/` endpoint and update the config.

- Or, a valid config file can also be created programmatically using the Evolver SDK

```python

from evolver.device import Evolver

Evolver.Config().save(settings.app_settings.CONFIG_FILE)

```

- Or, A valid config can be copied from another evolver instance.


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

We can leverage the tox testing environment, which contains all required dependencies, to run the application locally for evaluation:

#### Running **without** `evolver.yml` configuration file

```shellscript
EVOLVER_LOAD_FROM_CONFIG_ON_STARTUP=false tox -e test exec -- python -m evolver.app.main
```

#### Running **with** `evolver.yml` configuration file
```
tox -e test exec -- python -m evolver.app.main
```

You should then be able to visit the automatically generated API documentation in your local browser at
https://localhost:8080/docs (or https://localhost:8080/redoc). From there you can experiment with sending
data and reading from various endpoints (which will eventually be hooked up to a web user interface).

### Generate openapi schema as a JSON
To generate `openapi.json` in the project root run:

```
tox -e generate_openapi
```