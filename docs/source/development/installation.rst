Installing custom components
============================

Custom components are defined in python modules and can be installed via
standard python packaging tools such as pip. Generally these modules must be
installed onto the Raspberry Pi running the eVOLVER server, as they will be
loaded upon deserialization of the configuration file which references them.

For example, if you have a custom hardware driver defined in a python module
named `my_custom_hardware` within a public github repository, you can install it
using pip like so::

    # ssh into the Raspberry Pi running the eVOLVER server
    ssh pi@<evolver-ip-address>

    # then install the custom hardware package
    pip install --upgrade git+https://github.com/username/my-custom-hardware-package.git

Then, you can reference this custom hardware in your configuration file by using
its fully qualified class name (assuming you have defined a class implementing
a `SensorDriver` defined in the `my_custom_hardware.py` module), such as::

    hardware:
      MyCustomSensor:
        classinfo: "my_custom_hardware.MyCustomSensorDriver"
        config:
          addr: "custom_sensor_address"
          integrations: 1000


For more details on packaging and distribution of python components, see
https://packaging.python.org/en/latest/. This repository also serves as an
example of python packaging, and can be similarly installed via pip and git as
described above.