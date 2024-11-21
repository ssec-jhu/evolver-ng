import logging

EVENT = logging.INFO + 1
logging.addLevelName(EVENT, "EVENT")


class CaptureHandler(logging.Handler):
    def __init__(self, history_server):
        super().__init__()
        self.history_server = history_server

    def emit(self, record):
        vial = getattr(record, "vial", None)
        record_dict = {"level": record.levelname, "message": record.getMessage()}
        kind = "event" if record.levelno == EVENT else "log"
        self.history_server.put(record.name, kind, record_dict, vial=vial)
