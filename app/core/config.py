from pydantic_settings import SettingsConfigDict
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Expense Scanner"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"  # development, production, testing
    
    # PostgreSQL Configuration
    DATABASE_URL: str = "postgresql://user:password@localhost/expense_scanner"
    
    # Redis / Celery Configuration
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # AWS S3 Configuration
    AWS_ACCESS_KEY_ID: str | None = None
    AWS_SECRET_ACCESS_KEY: str | None = None
    AWS_REGION: str = "us-east-1"
    AWS_BUCKET_NAME: str = "expense-scanner-receipts"
    AWS_ENDPOINT_URL: str | None = None  # Used for LocalStack in development
    
    # AI / LLM Configuration
    LLM_PROVIDER: str = "ollama"  # ollama, openai, gemini
    OPENAI_API_KEY: str | None = None
    OPENAI_MODEL: str = "gpt-4o"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "qwen2.5vl:7b"
    GEMINI_API_KEY: str | None = None
    GEMINI_MODEL: str = "gemini-2.5-flash"


    # Auth / Google OAuth
    SECRET_KEY: str = "changeme"
    GOOGLE_CLIENT_ID: str = ""
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding='utf-8',
        extra='ignore',
        case_sensitive=True,
    )

settings = Settings()
