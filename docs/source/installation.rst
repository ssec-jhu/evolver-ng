Installation
============

Server
------

This guide is for installing the server on the Raspberry Pi mounted within the
eVOLVER hardware platform connected via serial to the physical hardware (see
:doc:`quick-start` for running the server locally with dummy hardware).

Requirements
~~~~~~~~~~~~

The application depends on python 3.11 or later, so ensure the Raspberry Pi os
is up to date and has at least this version of python installed. We recommend
using the debian based systems, such as bookworm
(see https://www.raspberrypi.com/software/operating-systems/).

If you are using the standard eVOLVER hardware, the Raspberry Pi should also be
setup to use the UART serial port available at ttyAMA0, which requires custom
bootflags in order to disable bluetooth and enable the serial port. This can be
done by adding the following to the /boot/firmware/config.txt file::

    [all]
    enable_uart=1
    dtoverlay=pi3-disable-bt

Install and setup service
~~~~~~~~~~~~~~~~~~~~~~~~~

* Install the package::

    pip install git+https://github.com/ssec-jhu/evolver-ng

* Setup the service to run on boot. Create a file at
  `/etc/systemd/system/evolver.service` with the following contents

    [Service]
    Environment=EVOLVER_HOST=0.0.0.0 EVOLVER_CONFIG_FILE=/etc/evolver.yml
    ExecStart=python -m evolver.app.main
    Restart=on-failure
    Type=exec


    [Install]
    WantedBy=multi-user.target

* Enable and start the service::

    sudo systemctl enable evolver
    sudo systemctl start evolver

The service should now be running and API listening at port 8080 for remote
connections. You can confirm this by navigating to the openapi documentation
interface at http://<raspberry-pi-ip>:8080/docs.

Configuration
~~~~~~~~~~~~~

The eVOLVER server needs to be configured with the hardware drivers that are
available on the system. This can be done either by creating or obtaining the
appropriate configuration file prior to server start. Alternatively the API/UI
can be used to update the configuration for a server that is already online.

.. note::
    There will be example configurations included in the evolver-ng package for
    many standard setups. The below advice may only be required in case of
    custom hardware.

Specifically, the `hardware` section should contain a map of the hardware on
box, where each element is a `ConfigDescriptor` that describes the hardware,
which contains a reference to the python class that implements the hardware
driver and the configuration for that driver. For example::

    hardware:
      OD90:
        classinfo: "evolver.hardware.standard.od_sensor.ODSensor"
        config:
          addr: "od90"
          integrations: 500

Note that since this references a python class, it is important that the package
in which that class is defined is installed in the python environment that runs
the server. For standard hardware, this is included in the evolver-ng package as
seen above. For custom hardware, maintainers should give instructions for
installing the package, and example configurations to simplify setup for
end-users. See :doc:`development/index` for more information on creating
extensions.

Web UI
------

We can similarly install the web UI on the Raspberry Pi, or any other computer
with network access to one or more eVOLVER servers.

The simplest way to install the web UI is to use mise to install npm, then build
the and run the service via npm.

* install mise (see also https://mise.jdx.dev/getting-started.html)::

    curl https://mise.run | sh

* install npm via mise::

    mise use node@lts

* clone the web UI repository::

    git clone https://github.com/ssec-jhu/evolver-ui

* build it::

    cd evolver-ui
    npm install
    npm run build

* run it::

    npm run start

Install and setup service
~~~~~~~~~~~~~~~~~~~~~~~~~

We can also setup the web UI to run as a service on the Raspberry Pi. Here is an
example systemd service file (for example at `/etc/systemd/system/evolver-ui.service`)::

  [Service]
  Requires=evolver.service
  ExecStart=/home/pi/evolver-ui/start-ui.sh
  WorkingDirectory=/home/pi/evolver-ui
  Restart=on-failure
  Type=exec

  [Install]
  WantedBy=multi-user.target

The above uses a helper script to start the UI that has been placed at the root
of the repository::

  #!/bin/sh
  export PATH=/home/pi/.local/share/mise/installs/node/22.15.0/bin:${PATH}
  cd /home/pi/evolver-ui
  npm start

After which you can enable and start the service::

    sudo systemctl enable evolver-ui
    sudo systemctl start evolver-ui

By default the UI will run on port 3000, so navigate your browser there and add
devices as necessary.