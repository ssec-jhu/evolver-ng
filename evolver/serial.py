from enum import Enum

import serial
import pydantic

from evolver.connection.interface import Connection


class SerialData(pydantic.BaseModel):
    addr: str
    data: list[bytes]
    kind: str = 'r'


class EvolverSerialUART(Connection):

    backend = serial

    class CMD(Enum):
        SEND_SUFFIX = b'_!'
        RESP_SUFFIX = b'end'

    class Config(pydantic.BaseModel):
        port: str = '/dev/ttyAMA0'
        baudrate: int = 9600
        timeout: float = 1

    def _open(self):
        return self.backend.Serial(port=self.config.port, baudrate=self.config.baudrate, timeout=self.config.timeout)

    def _close(self):
        return self.conn.close()

    @classmethod
    def _decode_serial_data(cls, response, suffix=CMD.RESP_SUFFIX.value):
        parts = response.split(b',')
        if (resp_suffix := parts.pop()) != suffix:
            raise ValueError(f"Incorrect command suffix detected: expected '{suffix}' but got '{resp_suffix}'")
        addrcode = parts[0].decode('utf-8')
        addr, code = addrcode[:-1], addrcode[-1]
        return SerialData(addr=addr, data=parts[1:], kind=code)

    @classmethod
    def _encode_serial_data(cls, cmd: SerialData, suffix=CMD.SEND_SUFFIX.value):
        addrcode = (cmd.addr + cmd.kind).encode('utf-8')
        return b','.join((addrcode, b','.join(cmd.data), suffix))

    def write(self, cmd, encode=True):
        return self.conn.write(self._encode_serial_data(cmd) if encode else cmd)

    def read(self):
        response = self.conn.readline()
        try:
            return self._decode_serial_data(response)
        except Exception as exc:
            raise ValueError(f'invalid response: {exc}') from exc

    def communicate(self, cmd: SerialData):
        # need to lock since we do three way comminication and during that term
        # the addressed device is considered owner of the line.
        with self.lock:
            self.write(cmd)
            data = self.read()
            ack = cmd.model_copy(update=dict(kind='a', data=[b'' for i in cmd.data]))
            self.write(ack)
        return data


class PySerialEmulator:
    """ For testing purposes only!. """

    @classmethod
    def Serial(cls, *args, **kwargs):
        return cls(*args, **kwargs)

    def __init__(self, *args, **kwargs):
        self._data = None

    def write(self, data):
        self._data = EvolverSerialUART._decode_serial_data(data, suffix=EvolverSerialUART.CMD.SEND_SUFFIX.value)

    def readline(self):
        if not self._data or self._data.addr.startswith('X'):
            return b'badresponse'
        data = self._data.model_copy()
        data.kind = 'e'
        return EvolverSerialUART._encode_serial_data(data, suffix=EvolverSerialUART.CMD.RESP_SUFFIX.value)

    def close(self):
        self._data = None


class EvolverSerialUARTEmulator(EvolverSerialUART):
    backend = PySerialEmulator
