import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Приложение
    APP_NAME: str = "ГО-ЧС Информирование"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # PostgreSQL
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "gochs"
    POSTGRES_USER: str = "gochs_user"
    POSTGRES_PASSWORD: str = ""

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = ""

    @property
    def REDIS_URL(self) -> str:
        return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/0"

    # JWT
    SECRET_KEY: str = "gochs-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60

    # Asterisk
    ASTERISK_HOST: str = "localhost"
    ASTERISK_AMI_PORT: int = 5038
    ASTERISK_AMI_USER: str = "gochs_ami"
    ASTERISK_AMI_PASSWORD: str = ""

    # Пути
    INSTALL_DIR: str = "/opt/gochs-informing"
    LOGS_DIR: str = "/opt/gochs-informing/logs"

    class Config:
        env_file = "/opt/gochs-informing/.env"
        extra = "ignore"


settings = Settings()
