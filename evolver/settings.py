from datetime import timedelta
from pathlib import Path

import pydantic_settings

from evolver.types import ExpireField


class BaseSettings(pydantic_settings.BaseSettings):
    model_config = pydantic_settings.SettingsConfigDict(env_prefix="EVOLVER_", case_sensitive=True)


class Settings(BaseSettings):
    CONNECTION_REUSE_POLICY_DEFAULT: bool = True
    DEFAULT_LOOP_INTERVAL: int = 20
    DEFAULT_NUMBER_OF_VIALS_PER_BOX: int = 16
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    ROOT_CALIBRATOR_FILE_STORAGE_PATH: Path = Path("calibration_files")
    EXPERIMENT_FILE_STORAGE_PATH: Path = Path("experiment_files")
    DEFAULT_CALIBRATION_EXPIRE: timedelta = ExpireField(default=timedelta(weeks=4 * 6))
    DATETIME_PATH_FORMAT: str = "%Y_%m_%dT%H_%M_%S"
    DEFAULT_TEMPERATURE_CALIBRATION_CONFIG_FILE: Path = (
        ROOT_CALIBRATOR_FILE_STORAGE_PATH / "default_temperature_calibration_config.yml"
    )
    AUTO_SAVE_NEW_CALIBRATIONS: bool = True


class AppSettings(BaseSettings):
    CONFIG_FILE: Path = Path("evolver.yml")  # in current directory
    LOAD_FROM_CONFIG_ON_STARTUP: bool = True
    HOST: str = "127.0.0.1"
    PORT: int = 8080


settings = Settings()
app_settings = AppSettings()
