from pathlib import Path

import pydantic_settings


class BaseSettings(pydantic_settings.BaseSettings):
    model_config = pydantic_settings.SettingsConfigDict(env_prefix="EVOLVER_", case_sensitive=True)


class Settings(BaseSettings):
    CONNECTION_REUSE_POLICY_DEFAULT: bool = True
    DEFAULT_LOOP_INTERVAL: int = 20
    DEFAULT_NUMBER_OF_VIALS_PER_BOX: int = 16


class AppSettings(BaseSettings):
    CONFIG_FILE: Path = Path("evolver.yml")  # in current directory
    LOAD_FROM_CONFIG_ON_STARTUP: bool = True
    HOST: str = "127.0.0.1"
    PORT: int = 8080


settings = Settings()
app_settings = AppSettings()
