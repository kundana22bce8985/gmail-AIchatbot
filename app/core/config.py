from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    groq_api_key: str

    model_config = SettingsConfigDict(
        env_file=r"D:\gmail-AIchatbot\.env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()