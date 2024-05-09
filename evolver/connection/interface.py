from abc import abstractmethod
from threading import RLock

from evolver.base import BaseConfig, BaseInterface
from evolver.settings import settings


class Connection(BaseInterface):
    """ Interface for a connection protocol, abstracting and wrapping lower-level communication over self.backend. """

    class Config(BaseConfig):
        ...

    backend = None  # Backend module/library to use.

    def __init__(self, *args, lock_constructor=RLock, **kwargs):
        self.conn = None  # This is the core object that this class wraps.
        self.lock = lock_constructor()
        super().__init__(*args, **kwargs)

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
            return self.conn.is_open() if callable(self.conn.is_open) else self.conn.is_open
        return self.conn is not None

    def open(self, *args, reuse: bool = settings.CONNECTION_REUSE_POLICY_DEFAULT, **kwargs):
        if not reuse:
            self.close()

        if not self.is_open():
            self.logger.info("Opening connection...")
            self.conn = self._open(*args, **kwargs)
            self.logger.info("Connection opened.")
        return self.conn

    def close(self, *args, **kwargs):
        if self.is_open():
            try:
                self.logger.info("Closing connection...")
                ret = self._close(*args, **kwargs)
                self.logger.info("Connection closed.")
                return ret
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
