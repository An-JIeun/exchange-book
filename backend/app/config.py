from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "meet-zool-api"
    app_env: str = "dev"
    database_url: str = "mysql+pymysql://root:password@localhost:3306/meet_zool"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
