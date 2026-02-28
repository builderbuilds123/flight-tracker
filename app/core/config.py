"""
Application Configuration
"""
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Application
    ENVIRONMENT: str = "development"
    SECRET_KEY: str = "your-secret-key-change-in-production"
    CORS_ORIGINS: str = "http://localhost:3000"
    
    # Database
    POSTGRES_USER: str = "flighttracker"
    POSTGRES_PASSWORD: str = "changeme"
    POSTGRES_DB: str = "flight_tracker"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: str = "5432"
    
    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: str = "6379"
    
    # API
    API_PORT: int = 8000
    API_HOST: str = "0.0.0.0"
    
    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"
    
    # Telegram Bot
    TELEGRAM_BOT_TOKEN: str = ""
    
    # Flight APIs
    AVIATION_STACK_API_KEY: str | None = None
    SKYSCANNER_API_KEY: str | None = None
    AMADEUS_API_KEY: str | None = None
    AMADEUS_API_SECRET: str | None = None
    
    # Email/Notifications
    SMTP_HOST: str | None = None
    SMTP_PORT: int = 587
    SMTP_USER: str | None = None
    SMTP_PASSWORD: str | None = None
    NOTIFICATION_EMAIL_FROM: str | None = None
    
    # Logging
    LOG_LEVEL: str = "INFO"
    
    @property
    def DATABASE_URL(self) -> str:
        """Construct database URL"""
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
    
    @property
    def REDIS_URL(self) -> str:
        """Construct Redis URL"""
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/0"
    
    @property
    def parsed_cors_origins(self) -> List[str]:
        """Parse CORS origins from comma-separated string"""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()
