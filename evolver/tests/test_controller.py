from evolver.controller.interface import Controller


class TestController(Controller):
    def pre_control(self, *args, **kwargs):
        return "pre control data"

    def control(self, *args, pre_control_output=None, **kwargs):
        assert pre_control_output == "pre control data"
        return pre_control_output + ", control data"

    def post_control(self, *args, control_output=None, **kwargs):
        assert control_output == "pre control data, control data"
        return control_output + ", post control data"


class TestControllerInterface:
    def test_hooks(self):
        assert TestController(evolver=None).run() == "pre control data, control data, post control data"
