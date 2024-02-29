import pytest
import evolver.serial
from evolver.serial import EchoSerial, SerialData, EvolverSerialUART


@pytest.fixture
def payload():
    return SerialData(addr=b'abc', data=[b'1', b'2'])


@pytest.fixture
def mockserial(monkeypatch):
    class MockSerial:
        def __init__(self, *args, **kwargs):
            pass
        def write(self, data):
            self._data = data
        def readline(self):
            if self._data.startswith(b'X'):
                return b'badresponse'
            return b'abce,1,2,end'
    monkeypatch.setattr(evolver.serial.serial, 'Serial', MockSerial)


def test_serial_interface_echo(payload):
    s = EchoSerial()
    resp = s.communicate(payload)
    assert resp == SerialData(addr=b'cba', data=payload.data, kind='e')


def test_uart_serial(mockserial, payload):
    s = EvolverSerialUART()
    response = s.communicate(payload)
    assert response == payload.model_copy(update=dict(kind='e'))


def test_uart_bad_response_raises(mockserial, payload):
    s = EvolverSerialUART()
    with pytest.raises(ValueError):
        epayload = payload.model_copy(update=dict(addr='Xyz'))
        s.communicate(epayload)
