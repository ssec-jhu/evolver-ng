import logging

EVENT = logging.INFO + 1
logging.addLevelName(EVENT, "EVENT")


class LogHistoryCaptureHandler(logging.Handler):
    def __init__(self, history_server):
        super().__init__()
        self.history_server = history_server

    def emit(self, record):
        vial = getattr(record, "vial", None)
        record_dict = {"level": record.levelname, "message": record.getMessage()}
        # TODO: add support for some extra fields (but these should be json-seralizable)
        kind = "event" if record.levelno == EVENT else "log"
        # we strip the package name from logger name since for history logs it
        # is redundant (used here for routing purposes) and without it we can
        # refer to entries by the common name within the system.
        name = record.name
        if name.startswith(f"{__package__}."):
            name = name[len(__package__) + 1 :]
        self.history_server.put(name, kind, record_dict, vial=vial)
