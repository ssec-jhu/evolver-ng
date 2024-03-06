import serial
from abc import ABC, abstractmethod
from pydantic import BaseModel
from threading import Lock


class SerialData(BaseModel):
    addr: str
    data: list[bytes]
    kind: str = 'r'


class Serial(ABC):
    class Config(BaseModel):
        pass

    def __init__(self, evolver = None, config: Config = None):
        self.evolver = evolver
        self.config = config or self.Config()

    @abstractmethod
    def communicate(cmd: SerialData) -> SerialData:
        pass


class EvolverSerialUART(Serial):
    class Config(BaseModel):
        port: str = '/dev/ttyAMA0'
        baudrate: int = 9600
        timeout: float = 1

    def __init__(self, evolver = None, config = None):
        super().__init__(config)
        self.serial = None
        self.lock = Lock()

    def _connect(self):
        self.serial = serial.Serial(port=self.config.port, baudrate=self.config.baudrate, timeout=self.config.timeout)

    def _parse_response(self, response):
        parts = response.split(b',')
        if parts.pop() != b'end':
            raise ValueError()
        addrcode = parts[0].decode('utf-8')
        addr, code = addrcode[:-1], addrcode[-1]
        return SerialData(addr=addr, data=parts[1:], kind=code)

    def _encode_command(self, cmd: SerialData):
        addrcode = (cmd.addr + cmd.kind).encode('utf-8')
        return b','.join((addrcode, b','.join(cmd.data), b'_!'))

    def communicate(self, cmd: SerialData):
        # need to lock since we do three way comminication and during that term
        # the addressed device is considered owner of the line.
        with self.lock:
            if self.serial is None:
                self._connect()
            self.serial.write(self._encode_command(cmd))
            response = self.serial.readline()
            try:
                data = self._parse_response(response)
            except Exception:
                raise ValueError('invalid response')
            ack = cmd.copy(update=dict(kind='a', data=[b'' for i in cmd.data]))
            self.serial.write(ack)
        return data


class EchoSerial(Serial):
    def communicate(self, cmd):
        return SerialData(addr=cmd.addr[::-1], data=cmd.data, kind=b'e')
