from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import model_validator


class Settings(BaseSettings):
    app_name: str = "meet-zool-api"
    app_env: str = "dev"
    database_url: str = "mysql+pymysql://root:password@localhost:3306/meet_zool"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @model_validator(mode="after")
    def validate_database_url_for_prod(self):
        db_url = (self.database_url or "").strip()
        if self.app_env == "prod" and (not db_url or "@localhost" in db_url or "@127.0.0.1" in db_url):
            raise ValueError("In prod, DATABASE_URL must point to a real external MySQL host (not localhost).")
        return self


settings = Settings()
