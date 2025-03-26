import logging

import pytest

from evolver.device import Evolver
from evolver.hardware.interface import SensorDriver
from evolver.history.demo import InMemoryHistoryServer
from evolver.logutils import EVENT, LogHistoryCaptureHandler, LogInfo


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


def test_log_evolver_hookup(caplog):
    # to prevent pytest from taking the records before they hit our handlers, we
    # need to set this higher than the level we are testing for below.
    caplog.set_level(logging.CRITICAL + 1)

    history = InMemoryHistoryServer()

    class HW(SensorDriver):
        def read(self):
            self.logger.warning("test from HW")
            self.logger.log(EVENT, "event from HW", extra=LogInfo(vial=1, event_class="something"))

    evolver = Evolver(history=history, hardware={"test": HW(name="test")})
    evolver.loop_once()
    log = history.get("test", "log").data["test"][0]
    assert log.data == {"level": "WARNING", "message": "test from HW"}
    event = history.get("test", "event", vials=[1]).data["test"][0]
    assert event.data == {"level": "EVENT", "message": "event from HW", "event_class": "something", "vial": 1}
    assert event.vial == 1
    assert history.get("test", "event", vials=[2]).data["test"] == []

    test_msg = "test outside evolver"
    logging.warning(test_msg)  # should not be captured since it is root logger
    for logs in history.get(kinds=["log"]).data.values():
        all_messages = [log.data["message"] for log in logs]
        assert test_msg not in all_messages


def test_log_info_helper():
    li = LogInfo(vial=1, event_class="something").dump()
    assert li == {LogInfo.EXTRA_KEY: {"vial": 1, "event_class": "something"}}
    assert list(li.keys()) == [LogInfo.EXTRA_KEY]
    assert li[LogInfo.EXTRA_KEY] == {"vial": 1, "event_class": "something"}
    with pytest.raises(ValueError):
        LogInfo(no_json=LogInfo)
    assert LogInfo.json_check({"no_json": LogInfo}, silent=True) == {}
