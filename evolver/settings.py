from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="EVOLVER_",
                                      case_sensitive=True)

    CONNECTION_REUSE_POLICY_DEFAULT: bool = True
    CONFIG_FILE: Path = Path('evolver.yml')  # in current directory
    HOST: str = "127.0.0.1"
    PORT: int = 8080


settings = Settings()
