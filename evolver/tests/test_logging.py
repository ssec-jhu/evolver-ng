import logging

from evolver.device import Evolver
from evolver.hardware.interface import SensorDriver
from evolver.history.demo import InMemoryHistoryServer
from evolver.logutils import EVENT, LogHistoryCaptureHandler


def test_log_capture_handler():
    history = InMemoryHistoryServer()
    handler = LogHistoryCaptureHandler(history)
    logger = logging.getLogger("test")
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logging.getLogger("test").info("test")
    hist = history.get("test", "log").data["test"][0]
    assert hist.data == {"level": "INFO", "message": "test"}
    assert hist.kind == "log"


def test_log_evolver_hookup():
    history = InMemoryHistoryServer()

    class HW(SensorDriver):
        def read(self):
            self.logger.warning("test from HW")
            self.logger.log(EVENT, "event from HW", extra={"vial": 1})

    evolver = Evolver(history=history, hardware={"test": HW(name="test")})
    evolver.loop_once()
    log = history.get("test", "log").data["test"][0]
    assert log.data == {"level": "WARNING", "message": "test from HW"}
    event = history.get("test", "event").data["test"][0]
    assert event.data == {"level": "EVENT", "message": "event from HW"}
    assert event.vial == 1

    test_msg = "test outside evolver"
    logging.warning(test_msg)  # should not be captured since it is root logger
    for logs in history.get(kinds=["log"]).data.values():
        all_messages = [log.data["message"] for log in logs]
        assert test_msg not in all_messages
