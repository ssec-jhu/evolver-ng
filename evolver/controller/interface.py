from abc import abstractmethod

from evolver.base import BaseConfig, BaseInterface


class Controller(BaseInterface):
    class Config(BaseConfig):
        ...

    def __init__(self, *args, evolver=None, **kwargs):
        self.evolver = evolver
        super().__init__(*args, **kwargs)

    def pre_control(self, *args, **kwargs):
        """ Hook for customization pre-control execution, see self.run().
            The return value is passed to control as ``self.control(pre_control_output=pre_control_output)``.
        """
        ...

    @abstractmethod
    def control(self, *args, pre_control_output=None, **kwargs):
        """ Main function to implement control procedure code. """
        ...

    def post_control(self, *args, control_output=None, **kwargs):
        """ Hook for customization post-control execution, see self.run().
            The value returned is also that returned from ``self.run()``.
        """
        return control_output

    def run(self, *args, **kwargs):
        """ Hook for customizing control execution. """
        pre_control_output = self.pre_control(*args, **kwargs)
        control_output = self.control(*args, pre_control_output=pre_control_output, **kwargs)
        return self.post_control(*args,  control_output=control_output, **kwargs)
