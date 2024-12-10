import json
import logging

from evolver.settings import settings

EVENT = logging.INFO + 1
logging.addLevelName(EVENT, "EVENT")


class LogInfo:
    """Helper class to provide "extra" to log records integrated with history.

    This class acts similar to a dict, but with all fields within a dict under a
    specific key and ensures the fields are json-serializable. Used with the
    history integration, fields provided will be available in the stored record.
    This is useful because all fields within extra are placed at the top level
    of a logrecord dict, so otherwise there is no way to distinguish them.

    Example:
        self.logger.log(EVENT, "Event message", extra=LogInfo(vial=1))
        self.logger.info(".", extra={"not_stored": 1, **LogInfo(vial=1).dump()})
    """

    EXTRA_KEY = "evolver_extra"

    @staticmethod
    def json_check(data, silent=False):
        if data == {}:
            return data
        try:
            json.dumps(data)
            return data
        except TypeError as e:
            if silent:
                return {}
            raise ValueError(f"Extra data must be json-serializable, got error: {e}")

    def __init__(self, **kwargs):
        self._dict = __class__.json_check(kwargs)

    def dump(self):
        return {self.EXTRA_KEY: self._dict}

    def __iter__(self):  # to integrate with logging, it inspects keys, then gets items.
        def iter():
            yield self.EXTRA_KEY

        return iter()

    def __getitem__(self, _):  # for logging, as above.
        return self._dict


class LogHistoryCaptureHandler(logging.Handler):
    def __init__(self, history_server):
        super().__init__()
        self.history_server = history_server

    def emit(self, record):
        extra = LogInfo.json_check(getattr(record, LogInfo.EXTRA_KEY, {}), silent=True)
        record_dict = {"level": record.levelname, "message": record.getMessage(), **extra}
        kind = "event" if record.levelno == EVENT else "log"
        # we strip the package name from logger name since for history logs it
        # is redundant (used here for routing purposes) and without it we can
        # refer to entries by the common name within the system.
        name = record.name
        if name.startswith(f"{settings.DEFAULT_LOGGER}."):
            name = name[len(__package__) + 1 :]
        self.history_server.put(name, kind, record_dict, vial=record_dict.get("vial", None))
