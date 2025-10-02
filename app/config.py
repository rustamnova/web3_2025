from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
	app_env: str = Field(default="dev", alias="APP_ENV")
	batch_limit: int = Field(default=50000, alias="BATCH_LIMIT")
	predict_timeout_sec: int = Field(default=180, alias="PREDICT_TIMEOUT_SEC")
	model_registry: str | None = Field(default=None, alias="MODEL_REGISTRY")
	# External services
	postgres_dsn: str | None = Field(default=None, alias="POSTGRES_DSN")
	clickhouse_dsn: str | None = Field(default=None, alias="CLICKHOUSE_DSN")
	rabbitmq_dsn: str | None = Field(default=None, alias="RABBITMQ_DSN")
	redis_dsn: str | None = Field(default=None, alias="REDIS_DSN")
	# CORS
	cors_origins: str | None = Field(default="*", alias="CORS_ORIGINS")
    
    # Pydantic v2 configuration
	model_config = SettingsConfigDict(
		env_file=".env",
		case_sensitive=False,
		protected_namespaces=("settings_",),
		extra="ignore",
	)


settings = Settings()  # load at import time for simplicity in this skeleton


