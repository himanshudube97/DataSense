from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://datasense:datasense@localhost:5463/datasense"
    JWT_SECRET_KEY: str = "change-me-to-a-random-secret-key"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    model_config = {"env_file": "../.env", "extra": "ignore"}


settings = Settings()
