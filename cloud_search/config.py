"""Re-export config from subpackage."""
import os
from pydantic import BaseModel


class Settings(BaseModel):
    """Application settings."""

    # OpenSearch configuration
    opensearch_host: str = os.getenv("OPENSEARCH_HOST", "localhost")
    opensearch_port: int = int(os.getenv("OPENSEARCH_PORT", "9200"))
    opensearch_user: str = os.getenv("OPENSEARCH_USER", "admin")
    opensearch_password: str = os.getenv("OPENSEARCH_PASSWORD", "admin")
    opensearch_use_ssl: bool = os.getenv("OPENSEARCH_USE_SSL", "false").lower() == "true"

    # JWT configuration
    jwt_secret: str = os.getenv("JWT_SECRET", "change-me-in-production")
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24 * 30  # 30 days

    # Rate limiting
    rate_limit_per_minute: int = 1000

    # Service configuration
    api_host: str = "0.0.0.0"
    api_port: int = int(os.getenv("PORT", "12000"))

    # Index defaults
    default_shards: int = 1
    default_replicas: int = 0

    class Config:
        extra = "allow"


settings = Settings()
