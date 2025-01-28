from abc import abstractmethod
from typing import Any

from pydantic import BaseModel

from evolver.base import BaseInterface


class HistoricDatum(BaseModel):
    timestamp: float
    kind: str
    vial: int | None
    data: Any


class HistoryResult(BaseModel):
    data: dict[str, list[HistoricDatum]]


class History(BaseInterface):
    class Config(BaseInterface.Config):
        pass

    @abstractmethod
    def put(self, name: str, kind: str, data: Any, vial: int = None):
        """Add data for hardware component to history.

        Args:
            name: The name of hardware component to save data for.
            data: The data to save. This MUST be a JSON-serializable object, as
                per the FastAPI json serialization requirements.
        """
        pass

    @abstractmethod
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
    ) -> HistoryResult:
        """Get saved history data.

        Implementations must override this method and return a HistoryResult object
        according to the input parameters, as listed below.

        Args:
            name: The name of hardware component to retrieve data for. If None,
                return all data.
            names: A list of names of hardware components to retrieve data for.
                Should be Mutually exclusive with the name parameter, where the
                name parameter would take precedence if supplied.
            t_start: The start time of the data to retrieve in floating point unix
                epoch seconds. If not specified, either n_max or an
                implementation-defined number of data points will be returned,
                prior to t_stop or now.
            t_stop: The stop time of the data to retrieve in floating point unix
                epoch seconds. If not specified, either n_max or an
                implementation-defined numer of data points will be returned,
                after t_start or up to now.
            n_max: The maximum number of data points to retrieve. If unspecified,
                an implementation-defined number of data points will be returned.
        """
        pass
