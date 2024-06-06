import pytest

from evolver.serial import EvolverSerialUARTEmulator, SerialData


@pytest.fixture
def payload():
    return SerialData(addr=b"abc", data=[b"1", b"2"])


def test_serial_interface_echo(payload):
    with EvolverSerialUARTEmulator() as s:
        resp = s.communicate(payload)
    assert resp == SerialData(addr=b"abc", data=payload.data, kind="e")


def test_uart_serial(payload):
    with EvolverSerialUARTEmulator() as s:
        response = s.communicate(payload)
    assert response == payload.model_copy(update=dict(kind="e"))


def test_uart_bad_response_raises(payload):
    with EvolverSerialUARTEmulator() as s:
        with pytest.raises(ValueError, match=r".* but got .*badresponse"):
            epayload = payload.model_copy(update=dict(addr="Xyz"))
            s.communicate(epayload)
