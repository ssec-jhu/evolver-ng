import json
import time
from collections import defaultdict, deque
from pathlib import Path

import duckdb
from fastapi.encoders import jsonable_encoder

from evolver.history.interface import HistoricDatum, History, HistoryResult
from evolver.settings import settings
from evolver.util import filter_vial_data


class HistoryServer(History):
    """Persistent history server.

    This history server stores data in newline-delimited JSON files, partitioned by time using the hive-style
    partitioning scheme. This allows for efficient querying of data by time range. The time-per-partition is
    configured via the `partition_seconds` parameter.
    """

    class Config(History.Config):
        name: str = "HistoryServer"
        experiment: str | None = None
        partition_seconds: int = 3600
        buffer_partitions: int = 3
        default_window: int = 3600
        default_n_max: int = 5000

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.history = defaultdict(list)
        self._experiment = self.experiment or getattr(kwargs.get("evolver", None), "experiment", "unspecified")
        self.history_dir = Path(settings.EXPERIMENT_FILE_STORAGE_PATH) / self._experiment / "history"
        self.json_hist_reader = f"""
            read_json('{self.history_dir}/*/history.json',
            format='newline_delimited',
            ignore_errors=true,
            columns={{timestamp: 'double', name: 'varchar', data: 'varchar'}},
            auto_detect=false,
            hive_partitioning=true)
            """
        self.current_partition = None
        self.current_file = None
        self.db = duckdb.connect(":memory:")
        self.db.execute("CREATE TABLE history (time_part INT, timestamp DOUBLE, name VARCHAR, data VARCHAR)")
        self._backfill_buffer()

    def _backfill_buffer(self):
        if self.buffer_partitions <= 0:
            return
        start_part = self._get_part(time.time() - self.partition_seconds * self.buffer_partitions)
        try:
            to_backfill = self.db.query(  # noqa: F841 - its used in the duckdb query below
                f"SELECT * FROM {self.json_hist_reader} WHERE time_part>=?",  # nosec: B608
                params=(start_part,),
            )
        except duckdb.IOException as exc:
            if "No files found" in str(exc):
                return
            raise
        self.db.execute("""INSERT INTO history (time_part, timestamp, name, data)
                        SELECT time_part, timestamp, name, data FROM to_backfill""")

    def _get_part(self, timestamp):
        if self.partition_seconds <= 0:
            return 0
        return int(timestamp / self.partition_seconds) * self.partition_seconds

    def _rotate(self, timestamp):
        partition = self._get_part(timestamp)
        if partition != self.current_partition:
            if self.current_file:
                self.current_file.close()
            self.current_partition = partition
            part_file = self.history_dir / f"time_part={partition}" / "history.json"
            part_file.parent.mkdir(parents=True, exist_ok=True)
            # open append mode in case we restart same experiment, we want to be able
            # to add records to existing partitions without cluttering many small files
            # and we only expect a single writer
            self.current_file = open(part_file, "a")
            # For expiration, special case is when partition seconds is 0, which
            # means no partitioning - likewise we don't expire anything.
            if self.buffer_partitions > 0 and self.partition_seconds > 0:
                expire_beyond = timestamp - self.partition_seconds * self.buffer_partitions
                self.db.execute("DELETE FROM history WHERE time_part<?", parameters=(expire_beyond,))

    def put(self, name: str, data):
        timestamp = time.time()
        self._rotate(timestamp)
        # if we append newlines at the end of each record, JSONL readers will
        # interpret last line as empty record, likewise for empty first line,
        # so append only if we are not at the beginning of the file.
        if self.current_file.tell() != 0:
            self.current_file.write("\n")
        record = {"timestamp": timestamp, "name": name, "data": jsonable_encoder(data)}
        json.dump(record, self.current_file)
        self.current_file.flush()
        if self.buffer_partitions > 0:
            self.db.execute(
                "INSERT INTO history (time_part, timestamp, name, data) VALUES (?, ?, ?, ?)",
                parameters=(self.current_partition, timestamp, name, json.dumps(jsonable_encoder(data))),
            )

    def get(
        self,
        name: str = None,
        t_start: float = None,
        t_stop: float = None,
        vials: list[int] | None = None,
        properties: list[str] | None = None,
        n_max: int = None,
    ):
        if t_start is None:
            t_start = (t_stop or time.time()) - self.default_window

        try:
            buffer_start_part = self._get_part(time.time() - self.partition_seconds * self.buffer_partitions)
            if t_start < buffer_start_part or self.buffer_partitions <= 0:
                query = f"SELECT * FROM {self.json_hist_reader}"  # nosec: B608
            else:
                query = "SELECT * FROM history"
            res = self.db.query(query)
        except duckdb.IOException as exc:
            if "No files found" in str(exc):
                return HistoryResult(data={})
            raise exc
        if name:
            res = res.filter(f"name='{name}'")
        if t_start:
            start_part = self._get_part(t_start)
            res = res.filter(f"time_part>={start_part}").filter(f"timestamp>={t_start}")
        if t_stop:
            stop_part = self._get_part(t_stop)
            res = res.filter(f"time_part<={stop_part}").filter(f"timestamp<{t_stop}")

        res = res.select("name", "timestamp", "data").order("timestamp DESC").limit(n_max or self.default_n_max)
        data = defaultdict(deque)

        while row := res.fetchone():
            row_data = row[2]
            # Attempt data cleaning and filtering, but pass data as-is if these
            # operations fail, in order to support arbitrary data shapes.
            try:
                # json only allows string keys, might want to revisit the assumptions
                # here, and/or have a more concrete vial-data container
                row_data = {int(k): v for k, v in json.loads(row_data).items()}
            except Exception:
                pass
            try:
                row_data = filter_vial_data(row_data, vials, properties)
            except Exception:
                pass
            if not row_data:
                continue

            data[row[0]].appendleft(HistoricDatum(timestamp=row[1], data=row_data))

        return HistoryResult(data=data)
