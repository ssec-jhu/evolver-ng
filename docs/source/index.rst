evolver-ng: The next generation eVOLVER control plane
=====================================================

This package provides a server application and interface specification for
remote configuration and control of eVOLVER systems. The system is designed to
be fully specified by a single configuration file, run without intervention for
long-running experiment durations, provide a well-defined web-API for remote
applications to design against, and be extended with new hardware and control
codes using a simple plugin system.

Check out the :doc:`quick-start` for if you want to get a feel for the system
without requiring installation on the eVOLVER hardware. If you are ready to
install the system on your eVOLVER hardware, check out the :doc:`installation`
documentation. If you have an eVOLVER ready to go, see :doc:`usage` for how to
get an experiment running on the hardware. Finally, if you would like to extend
by developing control codes or hardware drivers, see :doc:`development/index`.

.. note::

   This project is under active development.

.. note::

   In this guide we refer the the physical eVOLVER as a system or concept as
   "eVOLVER" (noting case) and to the software package components as "evolver"
   (the python module) or "evolver-ng" (the repository).

.. toctree::
   :maxdepth: 1

   quick-start
   installation
   concepts
   usage
   development/index.rst
   api