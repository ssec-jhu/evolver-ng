Evolver concepts
================

The evolver system is made up of several configurable components tied together
by a manager component that orchestrates the application control loop and
exposure to the web interface. Components can be grouped into two high level
categories:

* **Hardware and experiment control components**: These are the main target of
  extensions, representing the physical devices and experiment logic reading
  from and controlling them.

  * :py:class:`HardwareDriver<evolver.hardware.interface.HardwareDriver>`,
    specifically sensors that can be read
    (:py:class:`SensorDriver<evolver.hardware.interface.SensorDriver>`), and
    effectors that can be controlled
    (:py:class:`EffectorDriver<evolver.hardware.interface.EffectorDriver>`).

  * :py:class:`Controller<evolver.controller.interface.Controller>` which
    encompass the experiment logic.

  Included in the package are implementations for a variety of hardware and
  controllers.

* **Application layer components**: Components that manage the control loop,
  provide historical data, logging and interfacing to the web. These are
  configurable and can be extended to add new functionality, however modifying
  them should not be a prerequisite for adding new hardware or experiment logic.
  These include:

  * :py:class:`Evolver<evolver.device.Evolver>` which orchestrates the control
    loop.

  * :py:class:`History<evolver.history.interface.History>` which provides
    historical data.

  Included in the package are standard implementations of all of these
  components.


Configuration and ConfigDescriptors
-----------------------------------

All components in the evolver can be represented by a so-called
:py:class:`ConfigDescriptor<evolver.config.ConfigDescriptor>`. This is the key
component which translates from a static serialized configuration (e.g. that
which can be represented in a yaml file) to the in-memory instantiated objects
they describe. The `ConfigDescriptor` also enables the system to be extended
with pluggable modules for new hardware, controllers and other components
described above.

As an example, the serialized version - in the `evolver.yml` file - of a
particular hardware might look like:

.. code-block:: yaml

    hardware:
      temp:
        classinfo: "evolver.hardware.standard.od_sensor.ODSensor"
        config:
          addr: "od90"
          integrations: 500

The object under ``hardware.temp`` is recognized in the evolver system as a
``ConfigDescriptor``, where the object to create is an
``evolver.hardware.standard.od_sensor.ODSensor`` and the config to pass in will
be an evaluated version of its ``Config``. To clarify the point, consider the
following abbreviated definition of the ``ODSensor`` class::

    class ODSensor(SensorDriver):
        class Config(SensorDriver.Config):
            addr: str
            integrations: int = 500

As related to the above yaml configuration. We can see the top-level class
``ODSensor`` represented in ``classinfo`` and the config values as modeled in
the ``Config`` class represented within the ``config`` key.

.. _experiment_loop:

Experiment loop
---------------

In the normal mode, the evolver operates in a loop, continuously performing the
following steps in succession:

1. **Read sensors**: values are `read` and buffered within individual hardware
   drivers, for all configured sensors. For more on reading sensors and
   buffering see :ref:`buffering`.

2. **Execute controllers**: the `control` method of controllers is called for
   all controllers, in sequence. The controllers can `get` sensor values that
   have previously been read, and `set` effector values.

3. **Commit effector values**: effector values are `commit`ted for all
   configured effectors. This applies the changes `set` in the previous step to
   the underlying hardware. For more on why this is done in two steps see
   :ref:`buffering`.


These activities are coordinated in the
:py:class:`Evolver<evolver.device.Evolver>` class, via the
:py:meth:`loop_once<evolver.device.Evolver.loop_once>` method, and executed
continuously within the application. Configuration options `enable_control` and
`enable_commit` control whether the control (executing the `commit` method of
Controllers) and commit steps (executing the `commit` method of Effectors) are
executed, respectively.


.. _buffering:

Buffering
---------

Both Sensor and Effector drivers in the evolver system have separate methods for
reading/writing values to the underlying hardware device and for getting and
setting values in within the evolver software framework.

The primary reason for this separation is to simplify the operation of
potentially multiple controllers working against multiple vials, while
recognizing that the serial protocol for hardware on the standard evolver boxes
both:

* reads-to/writes-from *all* vials in a single serial communication, and
* incurs a significant latency overhead for each call that would prohibit making
  a large number of hardware read calls within a single loop.

The following advice should be taken then, depending on where in the system
development is taking place:

In Experiment code
~~~~~~~~~~~~~~~~~~
For a developer of a `Controller`, this means that:

* reads of sensor values should be done using the
  :py:meth:`get<evolver.hardware.interface.SensorDriver.get>` method of the
  `SensorDriver` interface, which will return the most recent value read from
  the read phase of the current loop.
* writes of effector values should be done using the
  :py:meth:`set<evolver.hardware.interface.EffectorDriver.set>` method of the
  `EffectorDriver` interface, which will buffer the value to be committed in the
  commit phase of the current loop.

These methods can be called as many times as required with no additional
penalty, simplifying the controller code, for example when looping over the set
of configured vials.

.. note::
  Note that values are typically neither read nor committed within the `control`
  method itself - these are executed by the evolver in the **read** and
  **commit** phases of :ref:`experiment_loop`. Multiple ``get`` calls would
  return the same values and subsequent ``set`` calls would overwrite the value
  to commit.

  While technically it is feasible to call the `read` and `commit` methods
  within a controller, we recommend against doing so. Due to the serial
  communication latency, and the fact that a commit will be done for all
  hardware by the system at the **commit** step, it is recommended that loop
  activity acts and submits proposals for only single value read-out.

In Hardware code
~~~~~~~~~~~~~~~~

For a developer of a `SensorDriver` or `EffectorDriver`, this means that:

* reads of sensor values should be done using the
  :py:meth:`read<evolver.hardware.interface.SensorDriver.read>` method of the
  `SensorDriver` interface, which must read the value from the underlying
  hardware device.
* writes of effector values should be done using the
  :py:meth:`commit<evolver.hardware.interface.EffectorDriver.commit>` method of
  the `EffectorDriver` interface, which must write the value to the underlying
  hardware device.
