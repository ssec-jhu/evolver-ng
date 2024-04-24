from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="EVOLVER_",
                                      case_sensitive=True)

    CONNECTION_REUSE_POLICY_DEFAULT: bool = True


settings = Settings()
