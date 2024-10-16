from http import HTTPStatus

from fastapi import HTTPException


class HardwareNotFoundError(HTTPException):
    def __init__(self, **kwargs):
        return super().__init__(status_code=HTTPStatus.NOT_FOUND, detail="Hardware not found", **kwargs)


class CalibratorNotFoundError(HTTPException):
    def __init__(self, **kwargs):
        return super().__init__(status_code=HTTPStatus.NOT_FOUND, detail="Hardware has no calibrator", **kwargs)


class OperationNotSupportedError(HTTPException):
    def __init__(self, exception, **kwargs):
        detail = f"Operation not supported: {exception}"
        return super().__init__(status_code=HTTPStatus.BAD_REQUEST, detail=detail, **kwargs)
