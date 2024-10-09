Evolver concepts
================

The evolver system is made up of several configurable components tied together
by a manager component that orchestrates the application control loop and
exposure to the web interface. Components can be grouped into two high level
categories:

* **Hardware and experiment control components**: These are the main target of extensions,
  representing the physical devices and experiment logic reading from and
  controlling them.

  * :py:class:`HardwareDriver<evolver.hardware.interface.HardwareDriver>`, specifically sensors that can be
    read (:py:class:`SensorDriver<evolver.hardware.interface.SensorDriver>`), and effectors that can be
    controlled (:py:class:`EffectorDriver<evolver.hardware.interface.EffectorDriver>`).

  * :py:class:`Controller<evolver.controller.interface.Controller>` which encompass the experiment
    logic.

  Included in the package are implementations for a variety of hardware and controllers.

* **Application layer components**: Components that manage the control loop, provide
  historical data, logging and interfacing to the web. These are configurable
  and can be extended to add new functionality, however modifying them should
  not be a prerequisite for adding new hardware or experiment logic. These
  include:

  * :py:class:`Evolver<evolver.device.Evolver>` which orchestrates the control loop.

  * :py:class:`History<evolver.history.interface.History>` which provides
    historical data.

  Included in the package are standard implementations of all of these components.


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


.. _buffering:

buffering
---------

