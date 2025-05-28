Config
======

Each pluggable component within the eVOLVER system is defined as a python class
which itself contains a `Config` class that defines optional and required data
affecting the behavior of the component that is used for serialization,
deserialization, and UI form creation (see also :ref:`config`).

The config class
----------------

The config classes are based on [pydantic](https://docs.pydantic.dev/latest/)
models which leverage type annotations on class data members to define the data
schema.

As an example, consider the following abbreviated definition of a controller
class, which is a pluggable component in the eVOLVER system::

    class MyController(Controller):
        class Config(Controller.Config):
            param_required: float
            param_optional: int = 10  # has a default value
            param_optional_with_desc: str = Field(default="default", description="A string parameter")

You can observe several things here:

* The `Config` class is a nested class within the component class, which is a
  common pattern in eVOLVER components. This is a convenience that keeps the
  definition clearly in the context in which it is used, and enables the system
  to access the config as a standard-defined class attribute (i.e.
  `MyController.Config`).
* The `Config` class inherits from the parent component's `Config` class, which
  allows it to extend the configuration with additional parameters while still
  inheriting the base configuration.
* The data members of the `Config` class are defined with type annotations. This
  is a requirement from pydantic that enables it to both validate the data,
  reliably perform serialization, and generate a json-schema that con be used to
  dynamically generate UI forms.
* The `Field` function can be used to provide additional metadata about the
  particular field such as a description and validation rules (see
  https://docs.pydantic.dev/latest/api/fields/#pydantic.fields.Field)


Note that while the eVOLVER system adds additional functionality - such as
from-file loading and automatic handling of eVOLVER components defined in the
config - pydantic does most of the heavy lifting here, so see its documentation
for information on how to apply custom validations or otherwise extend the
config models.

Serialized configuration
------------------------

The config classes described above are what enable the eVOLVER system to be
described within a static yaml file (e.g. `evolver.yml`), and be configured over
the wire via the web API.

In the serialized configuration, we describe a component by its class and the
data members to set on its config. This is done via a
:py:class:`ConfigDescriptor<evolver.config.ConfigDescriptor>`. For example, the
above `MyController` class can be described in the serialized configuration as
follows (assuming it is defined in `my_module`)::

        classinfo: "my_module.MyController"
        config:
          param_required: 3.14
          param_optional_with_desc: "Hello, world!"

JSON schema
-----------

The web API also provides and endpoint to retreive the JSON schema for the
configuration of a particular component by its fully qualified class name::

    GET /schema/?classinfo={component_name}


might return something like:

.. code-block:: json

    {
        "classinfo": "my_module.MyController",
        "config": {
            "properties": {
                "name": {
                    "anyOf": [
                        {
                            "type": "string"
                        },
                        {
                            "type": "null"
                        }
                    ],
                    "default": null,
                    "title": "Name"
                },
                "param_required": {
                    "title": "Param Required",
                    "type": "number"
                },
                "param_optional": {
                    "default": 10,
                    "title": "Param Optional",
                    "type": "integer"
                },
                "param_optional_with_desc": {
                    "default": "default",
                    "description": "A string parameter",
                    "title": "Param Optional With Desc",
                    "type": "string"
                }
            },
            "required": [
                "param_required"
            ],
            "title": "Config",
            "type": "object"
        }
    }


which contains enough information to generate a UI form for the component's
configuration.

Component initialization and configuration
------------------------------------------

When a component is initialized via a config descriptor (e.g. when reading the
configuration file on startup or via the web update API - specifically by
calling :py:meth:`create<evolver.base.ConfigDescriptor.create>` on config
descriptor or :py:meth:`create` on the base interface), by default the members
of its `config` are unpacked and passed to the components constructor. Then the
base class for components
(:py:class:`BaseInterface<evolver.base.BaseInterface>`) will automatically
assign the config members to the component instance as attributes.

This effectively means that parameters in the config are also class parameters
and can be directly accessed and used within the component logic. In the example
above, this means that the control code in `MyController` could access
`self.param_required`, as in::

    class MyController(Controller):
        <<<...>>>
        def control(self):
            if self.param_required > 0:
                # do something based on the required parameter
                <<<...>>>

.. warning::
    This has an implication on the mutability of the class parameters that share
    a name with the config members: due to the serializability requirements of
    components, such members should also be serializable and compatible with the
    config model. For example, if `param` has a type hint of `float` in the config
    model, then setting `self.param = "string"` will violate the type validation
    on serialization and may cause errors in the application.
