from fastapi import HTTPException


class HardwareNotFoundError(HTTPException):
    def __init__(self, **kwargs):
        return super().__init__(status_code=404, detail="Hardware not found", **kwargs)


class CalibratorNotFoundError(HTTPException):
    def __init__(self, **kwargs):
        return super().__init__(status_code=404, detail="Hardware has no calibrator", **kwargs)
