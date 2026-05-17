from pydantic_settings import SettingsConfigDict
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Expense Scanner"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # PostgreSQL Configuration
    DATABASE_URL: str = "postgresql://user:password@localhost/expense_scanner"
    
    # Redis / Celery Configuration
    REDIS_URL: str = "redis://localhost:6379/0"
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding='utf-8',
        extra='ignore',
        case_sensitive=True,
    )

settings = Settings()
