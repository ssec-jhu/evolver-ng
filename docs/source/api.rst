API
===

Configuration
-------------

.. autosummary::
   :toctree: generated

   evolver.base.ConfigDescriptor
   evolver.base.ConfigDescriptor.create

Hardware Extension Points
-------------------------

.. autosummary::
   :toctree: generated

   evolver.hardware.interface.HardwareDriver
   evolver.hardware.interface.SensorDriver
   evolver.hardware.interface.SensorDriver.read
   evolver.hardware.interface.SensorDriver.get
   evolver.hardware.interface.EffectorDriver
   evolver.hardware.interface.EffectorDriver.commit
   evolver.hardware.interface.EffectorDriver.set
   evolver.hardware.interface.HardwareDriver._transform

Calibration Extension Points
----------------------------
.. autosummary::
   :toctree: generated

   evolver.calibration.interface.Calibrator
   evolver.calibration.interface.Calibrator.create_calibration_procedure
   evolver.calibration.interface.Calibrator.init_transformers
   evolver.calibration.procedure.CalibrationProcedure
   evolver.calibration.interface.Transformer
   evolver.calibration.interface.Transformer.fit
   evolver.calibration.interface.Transformer.convert_to
   evolver.calibration.interface.Transformer.convert_from

Experiment Control Extension Points
-----------------------------------

.. autosummary::
   :toctree: generated

   evolver.controller.interface.Controller
   evolver.controller.interface.Controller.control

Evolver manager
---------------

.. autosummary::
   :toctree: generated

   evolver.device.Evolver
