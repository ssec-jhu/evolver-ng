from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="EVOLVER_",
                                      case_sensitive=True)

    CONNECTION_REUSE_POLICY_DEFAULT: bool = True
    OPEN_DEVICE_CONNECTION_UPON_INIT_POLICY_DEFAULT: bool = False
    ROOT_CALIBRATOR_FILE_STORAGE_PATH: str = '.'


settings = Settings()
