eVolver-ng: The next generation eVolver control plane
=====================================================

This package provides a server application and interface specification for
remote configuration and control of eVolver systems. The system is designed to
be fully specified by a single configuration file, run without intervention for
long-running experiment durations, provide a well-defined web-API for remote
applications to design against, and be extended with new hardware and control
codes using a simple plugin system.

Check out the :doc:`quick-start` for if you want to get a feel for the system
without requiring installation on the eVolver hardware. If you are ready to
install the system on your eVolver hardware, check out the :doc:`installation`
documentation. If you have an eVolver ready to go, see :doc:`usage` for how to
get an experiment running on the hardware. Finally, if you would like to extend
by developing control codes or hardware drivers, see :doc:`development/index`.

.. note::

   This project is under active development.

.. toctree::
   :maxdepth: 1

   quick-start
   installation
   usage
   development/index.rst
   concepts
   api