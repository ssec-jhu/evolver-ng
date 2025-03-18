from http import HTTPStatus

from fastapi import HTTPException


class EvolverNotFoundError(HTTPException):
    def __init__(self, **kwargs):
        return super().__init__(status_code=HTTPStatus.NOT_FOUND, detail="Evolver not found", **kwargs)


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


class CalibratorProcedureSaveError(HTTPException):
    def __init__(self, **kwargs):
        return super().__init__(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR, detail="Unable to save calibration procedure", **kwargs
        )


class CalibratorProcedureApplyError(HTTPException):
    def __init__(self, detail: str = "Unable to apply calibration procedure", **kwargs):
        return super().__init__(status_code=HTTPStatus.INTERNAL_SERVER_ERROR, detail=detail, **kwargs)


class CalibrationProcedureActionNotFoundError(HTTPException):
    def __init__(self, action_name: str, **kwargs):
        return super().__init__(status_code=HTTPStatus.NOT_FOUND, detail=f"Action '{action_name}' not found", **kwargs)


class CalibrationProcedureNotFoundError(HTTPException):
    def __init__(self, **kwargs):
        return super().__init__(
            status_code=HTTPStatus.NOT_FOUND,
            detail="No in progress calibration procedure was found. Please start a new calibration procedure",
            **kwargs,
        )
