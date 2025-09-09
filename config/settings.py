"""
Configuration settings for the AI-Powered Patient Risk Prediction platform.

This module defines all application settings including API configuration,
security settings, database configuration, ML model parameters, and HIPAA compliance.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Application settings configuration using Pydantic BaseSettings.

    Settings can be overridden via environment variables or .env file.
    All settings include sensible defaults for development.
    """

    # Application Settings
    app_name: str = "AI-Powered Patient Risk Prediction Platform"
    app_version: str = "1.0.0"
    debug: bool = True

    # API Settings
    api_v1_prefix: str = "/api/v1"
    host: str = "0.0.0.0"
    port: int = 8000

    # Security Settings
    secret_key: str = "your-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # Database Settings
    database_url: str = "duckdb:///./data/healthcare.db"

    # ML Model Settings
    model_path: str = "./data/models"
    risk_threshold_high: float = 0.8
    risk_threshold_medium: float = 0.5

    # NLP Settings
    huggingface_model: str = "emilyalsentzer/Bio_ClinicalBERT"
    max_sequence_length: int = 512

    # Logging Settings
    log_level: str = "INFO"
    log_file: str = "./logs/app.log"

    # HIPAA Compliance
    encrypt_pii: bool = True
    audit_logging: bool = True
    session_timeout: int = 1800  # 30 minutes

    class Config:
        """Pydantic configuration for settings loading."""

        env_file = ".env"
        case_sensitive = False


settings = Settings()
