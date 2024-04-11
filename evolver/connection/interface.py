from abc import ABC, abstractmethod
from threading import RLock

import pydantic


class Connection(ABC):
    """ Interface for a connection protocol, abstracting and wrapping lower-level communication over self.backend. """

    class Config(pydantic.BaseModel):
        ...

    backend = None  # Backend module/library to use.

    def __init__(self, *args, config: Config = None, lock_constructor=RLock, **kwargs):
        self.conn = None  # This is the core object that this class wraps.
        self.config = config or self.Config()
        self.lock = lock_constructor()

    @abstractmethod
    def _open(self,  *args, **kwargs):
        """ Open a connection using self.backend and return connection instance to be assigned to self.conn by
            self.open(). See self.open() & self.__enter__().
        """
        ...

    @abstractmethod
    def _close(self, *args, **kwargs):
        """ Close the connection using either self.backend or self.conn. See self.close() & self.__exit__(). """
        ...

    @abstractmethod
    def read(self, *args, **kwargs):
        """ Implement read protocol. """
        ...

    @abstractmethod
    def write(self, *args, **kwargs):
        """ Implement write protocol. """
        ...

    @abstractmethod
    def communicate(self, *args, **kwargs):
        """ Implement write/read protocol all in one. """
        ...

    def is_open(self):
        if hasattr(self.conn, "is_open"):
            return self.conn.is_open()

        return self.conn is not None

    def open(self, *args, reuse=True, **kwargs):
        if not reuse:
            self.close()

        if not self.is_open():
            self.conn = self._open(*args, **kwargs)
        return self.conn

    def close(self, *args, **kwargs):
        if self.is_open():
            try:
                return self._close(*args, **kwargs)
            finally:
                # NOTE: We assume here that a failure when closing renders the connection undefined so nullify.
                self.conn = None

    def __del__(self):
        self.close()

    def __enter__(self):
        self.lock.acquire()
        try:
            self.open()
        except Exception:
            self.lock.release()
            raise
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            self.close()
        finally:
            self.lock.release()
