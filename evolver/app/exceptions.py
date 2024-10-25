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


class CalibratorCalibrationDataNotFoundError(HTTPException):
    def __init__(self, **kwargs):
        return super().__init__(
            status_code=HTTPStatus.NOT_FOUND, detail="Calibrator's calibration data not found", **kwargs
        )


class CalibratorCalibrationProcedureFailedToInitializeError(HTTPException):
    def __init__(self, **kwargs):
        return super().__init__(
            status_code=HTTPStatus.BAD_REQUEST, detail="Could not initialize the calibration procedure", **kwargs
        )


class CalibrationProcedureActionNotFoundError(HTTPException):
    def __init__(self, action_name: str, **kwargs):
        return super().__init__(status_code=HTTPStatus.NOT_FOUND, detail=f"Action '{action_name}' not found", **kwargs)


class CalibrationProcedureActionInvalidPayloadError(HTTPException):
    def __init__(self, errors: list[str], **kwargs):
        return super().__init__(status_code=HTTPStatus.BAD_REQUEST, detail=f"Invalid payload: {errors}", **kwargs)
