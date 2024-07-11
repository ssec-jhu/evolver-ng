from collections import defaultdict
from enum import Enum

import serial

from evolver.base import BaseConfig
from evolver.connection.interface import Connection


class SerialData(BaseConfig):
    addr: str
    data: list[bytes]
    kind: str = "r"


class EvolverSerialUART(Connection):
    backend = serial

    class CMD(Enum):
        SEND_SUFFIX = b"_!"
        RESP_SUFFIX = b"end"

    class Config(BaseConfig):
        name: str = "EvolverSerialUART"
        port: str = "/dev/ttyAMA0"
        baudrate: int = 9600
        timeout: float = 1

    def _open(self):
        return self.backend.Serial(port=self.port, baudrate=self.baudrate, timeout=self.timeout)

    def _close(self):
        return self.conn.close()

    @classmethod
    def _decode_serial_data(cls, response, suffix=CMD.RESP_SUFFIX.value):
        parts = response.split(b",")
        if (resp_suffix := parts.pop()) != suffix:
            raise ValueError(f"Incorrect command suffix detected: expected '{suffix}' but got '{resp_suffix}'")
        addrcode = parts[0].decode("utf-8")
        addr, code = addrcode[:-1], addrcode[-1]
        return SerialData(addr=addr, data=parts[1:], kind=code)

    @classmethod
    def _encode_serial_data(cls, cmd: SerialData, suffix=CMD.SEND_SUFFIX.value):
        addrcode = (cmd.addr + cmd.kind).encode("utf-8")
        return b",".join((addrcode, b",".join(cmd.data), suffix))

    def write(self, cmd, encode=True):
        return self.conn.write(self._encode_serial_data(cmd) if encode else cmd)

    def read(self):
        response = self.conn.readline()
        try:
            return self._decode_serial_data(response)
        except Exception as exc:
            raise ValueError(f"invalid response: {exc}") from exc

    def communicate(self, cmd: SerialData):
        # need to lock since we do three way comminication and during that term
        # the addressed device is considered owner of the line.
        with self.lock:
            self.write(cmd)
            data = self.read()
            ack = cmd.model_copy(update=dict(kind="a", data=[b"" for i in cmd.data]))
            self.write(ack)
        return data


class PySerialEmulator:
    """For testing purposes only!."""

    raw_response_map = {}
    hits_map = defaultdict(int)

    @classmethod
    def Serial(cls, *args, **kwargs):
        return cls(*args, **kwargs)

    def __init__(self, *args, **kwargs):
        self._data = None
        self._data_raw = None

    def write(self, data):
        self._data_raw = data
        self.hits_map[data] += 1
        self._data = EvolverSerialUART._decode_serial_data(data, suffix=EvolverSerialUART.CMD.SEND_SUFFIX.value)

    def readline(self):
        if mapped_response := self.raw_response_map.get(self._data_raw):
            return mapped_response
        if not self._data or self._data.addr.startswith("X"):
            return b"badresponse"
        data = self._data.model_copy()
        data.kind = "e"
        return EvolverSerialUART._encode_serial_data(data, suffix=EvolverSerialUART.CMD.RESP_SUFFIX.value)

    def close(self):
        self._data = None


class EvolverSerialUARTEmulator(EvolverSerialUART):
    backend = PySerialEmulator


def create_mock_serial(raw_response_map):
    class ResponseBackendEmulator(PySerialEmulator):
        pass

    ResponseBackendEmulator.raw_response_map = raw_response_map
    ResponseBackendEmulator.hits_map = defaultdict(int)

    class SerialEmulator(EvolverSerialUART):
        backend = ResponseBackendEmulator

    return SerialEmulator()
