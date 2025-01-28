import time
from collections import defaultdict, deque

from evolver.history.interface import HistoricDatum, History, HistoryResult
from evolver.util import filter_data_properties


class InMemoryHistoryServer(History):
    class Config(History.Config):
        name: str = "HistoryServer"
        buffer_size: int = 100

    def __init__(self, *args, **kwargs):
        self.history = defaultdict(lambda: deque(maxlen=self.buffer_size))
        super().__init__(*args, **kwargs)

    def put(self, name, kind, data, vial=None):
        self.history[name].append(HistoricDatum(timestamp=time.time(), data=data, kind=kind, vial=vial))

    def get(
        self,
        name: str = None,
        names: list[str] = None,
        kinds: list[str] = None,
        t_start: float = None,
        t_stop: float = None,
        vials: list[int] | None = None,
        properties: list[str] | None = None,
        n_max: int = None,
    ):
        query_names = self.history.keys()
        if name is not None:
            query_names = [n for n in query_names if n == name]
        elif names is not None:
            query_names = [n for n in query_names if n in names]
        data = {}
        for n in query_names:
            history = list(self.history[n])[:n_max]
            try:
                history = [filter_data_properties(d, properties) for d in history]
            except Exception:
                pass

            def filter_records(record):
                if kinds and record.kind not in kinds:
                    return False
                if vials and record.vial not in vials:
                    return False
                return True

            data[n] = [i for i in history if filter_records(i)]
        return HistoryResult(data=data)
