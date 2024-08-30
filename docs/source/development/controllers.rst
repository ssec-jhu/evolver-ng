Developing a new controller
===========================

In eVolver controllers are the components that implement experiment logic. They
can read the state and history of the eVolver environment (e.g. the sensor
values) and subsequently modify it (via effectors). In a typical eVolver setup
controller logic is executed once during a device loop, after reading the state
of all sensors. See :doc:`/concepts` for more details on the device
operation.

Controllers are implemented as Python classes that inherit from the
:class:`evolver.controller.Controller` class, the logic of which is executed via
a call to the :meth:`evolver.controller.Controller.control` method. Developing a
new controller is a matter of implementing this method. Within
:meth:`evolver.controller.Controller.control`, code can read sensor values (e.g.
by calling :meth:`evolver.hardware.interface.SensorDriver.get`) and effect the
environment based on read sensor values (e.g. by calling
:meth:`evolver.hardware.interface.EffectorDriver.set` with appropriate input).

As with other eVolver components, controllers contain `Config` classes that
define the configuration options for the experiment, which can be read from
on-disk config and modified via the API and UIs. authors should provide a
`Config` class that inherits from :class:`evolver.controller.Controller.Config`
with appropriate options for the experiment. See :doc:`config` for
more details on configuration.

Getting started
---------------

A breif example will help illustrate what is required to implement a new
controller. In the example below, we define a simple experiment::

    from evolver.controller import Controller
    from evolver.hardware.standard import Temperature

    class MyController(Controller):
        class Config(Controller.Config):
            limit: int = 42
            hysteresis: int = 2

        def control(self):
            for vial in self.vials:
                density = self.evolver.hardware['temp'].get[vial].density
                if density > self.limit:
                    self.evolver.hardware['temp'].set(Temperature.Input(vial=vial, value=30))
                elif density < self.limit - self.hysteresis:
                    self.evolver.hardware['temp'].set(Temperature.Input(vial=vial, value=38))

In the above you can note that all the business logic is contained within the
`control` method, while configuration parameters are available as attributes of
the controller (e.g. `self.limit` and `self.hysteresis`). Further, the
controller gains access to hardware state via the `evolver` property, which is
an instance of :py:class:`evolver.device.Evolver`, and can be used to access
hardware drivers (e.g. `self.evolver.hardware['temp']`) to get current state and
set desired state.

.. note::

    The `evolver` property comes from hookup to the device (which happens for
    example in creating a new eVolver from configuration), see also
    :ref:`evolver-hookup` below. `vials` comes from the base controller `Config`
    class, and represents a list of vials to operate on.

Support multiple vial configurations
------------------------------------

You might note in the above example that:

* We loop over a set of vials in the controller, and
* We have scalar values for the config parameters, not an array of values for
  each vial.

The concept here is that each instance of a controller is a specific instance of
the experiment on a set of vials. In the simplest case one experiment with a
given set of configuration parameters is run on all vials on the box. The
eVolver accepts a list of controllers, however, which can represent either
distinct experiment logic on separate vials, or distinctly configured instances
of the same experiment on separate vials.

For example, given the above experiment, and end-user could run on half the
vials with a different set of parameters as follows:

.. code-block:: yaml

    controllers:
      - classinfo: mymodule.MyController
        config:
          vials: [0, 1, 2, 3, 4, 5, 6, 7]
          limit: 42
          hysteresis: 2
      - classinfo: mymodule.MyController
        config:
          vials: [8, 9, 10, 11, 12, 13, 14, 15]
          limit: 20
          hysteresis: 1


Testing the controller
----------------------

Because the controllers main function is to modify the environment based on
inputs, we can test a controller by mocking the hardware dependencies and
asserting expected outputs are sent to particular hardware.

We are currently working on a testing framework for eVolver controllers (please
see https://github.com/ssec-jhu/evolver-ng/issues/156), but in the meantime, an
example for mocking hardware within an eVolver environment can be seen in the
`test_chemostat.py` file in the eVolver repository.


Logging in the controller
-------------------------

All components in the eVolver framework contain in internal logger which is an
instance of a python standard library `logging.Logger`. This logger can be used
to emit messages from within a controller which, unless otherwise configured,
will get routed through the eVolver logging mechanism.

.. note::

    At present, the logger is configured only with basic handling, and will
    print to stdout. In future releases more advanced logging and event handling
    is planned, along with retreival of logs from the API.


Example::

    class MyController(Controller):
        def control(self):
            self.logger.info('Starting control loop')
            for vial in self.vials:
                self.logger.debug(f'Processing vial {vial}')
                ...


History
-------

Some experiments may require access to historical data in order to make control
decisions. While it is always possible to store a buffer of historic data for a
given sensor in memory within the controller, this may have unintended
consequences in the case of reboot or even a reconfiguration of the eVolver
(which reallocates all objects): the buffer would be lost.

eVolver provides a history server which is backed by persistent storage designed
to be queried via the API or within a controller. This means controllers code
can remain simple and focus on core logic, as opposed to maintaining file-based
historic data or error-prone in-memory buffers.

To access the history server, the controller can use the `self.evolver.history`
property which is automatically available to all controllers when used within
the application (see :ref:`evolver-hookup` below).

For example::

        class MyController(Controller):
            def control(self):
                # Get the temperature history for all vials for past hour
                temp_history = self.evolver.history.get('temp', t_start=time.time() - 3600)
                for vial in self.vials:
                    mean_temp = np.mean([i.data[0]['value'] for i in  history.get(name='test').data['test']])

.. note::

    The response from the history server
    :py:class:`evolver.history.HistoryResult` is amenable to transport over the
    network, but presently has overhead in working with results in the
    interpreter (as can be noted in the above example). Functionality like
    `to_dataframe` or `to_numpy` can be provided in future versions.


.. _evolver-hookup:

Evolver hookup and portability
------------------------------

You might notice that the controller in the example above implicitly requires an
instance of `evolver.device.Evolver` to be passed into its constructor, in order
to access the hardware it needs. The framework normally does this for you (it
will both construct the object and pass in the Evovler), but it may be desired
to have a controller which depends only on that which is specified in its config
and takes in hardware explicitly, which can operate independently of the
application framework.

To do this while also supporting usage within the application, it is recommended
to specify hardware in the Config which have types accepting either a string or
hardware class, then a property which dispatches appropriately, for example::

    class MyController(Controller):
        class Config(Controller.Config):
            temp_sensor: str|Temperature|ConfigDescriptor

        @property
        def temp_sensor_hw(self):
            if isinstance(self.temp_sensor, str):
                return self.evolver.hardware[self.temp_sensor]
            return self.temp_sensor

In the above case, when the controller operates within the application, the
temp_sensor will be specified as the name of the hardware in the evolver
configuration file, and the controller will use the hardware instance from the
evolver.

If the controller should be instantiated outside the framework (and without an
evolver instance), the instantiated Temperature object can be passed in
directly::

    temp_sensor = Temperature()
    controller = MyController(temp_sensor=temp_sensor)

Finally, if a ConfigDescriptor (the config object representing how to construct
the appropriate class) is supplied, it will automatically be processed and
instantiated::

    descriptor = ConfigDescriptor(classinfo='evolver.hardware.standard.Temperature')
    controller = MyController(temp_sensor=descriptor)

or with a dict, from create::

    config = {'temp_sensor': {'classinfo': 'evolver.hardware.standard.temperature.Temperature'}}
    controller = MyController.create(config)