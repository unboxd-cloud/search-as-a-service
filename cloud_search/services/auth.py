"""Authentication service."""
import os
import secrets
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel
from jose import jwt
from passlib.context import CryptContext


class Settings(BaseModel):
    """Application settings."""
    jwt_secret: str = os.getenv("JWT_SECRET", "change-me-in-production")
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24 * 30

    class Config:
        extra = "allow"


settings = Settings()

from cloud_search.models import APIKey, Tenant, APIKeyResponse

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class InMemoryStore:
    """Simple in-memory storage for tenants and API keys."""
    
    def __init__(self):
        self.tenants: dict[str, Tenant] = {}
        self.api_keys: dict[str, APIKey] = {}
        self.api_key_index: dict[str, str] = {}  # key_value -> api_key_id
        self._create_demo_tenant()
    
    def _create_demo_tenant(self):
        """Create a demo tenant for testing."""
        tenant_id = "demo"
        key_value = f"cs_demo_{secrets.token_urlsafe(32)}"
        
        tenant = Tenant(
            id=tenant_id,
            name="Demo User",
            email="demo@example.com",
            created_at=datetime.utcnow(),
            is_active=True,
        )
        
        api_key = APIKey(
            id=str(uuid.uuid4()),
            key=key_value,
            tenant_id=tenant_id,
            name="Demo Key",
            created_at=datetime.utcnow(),
            is_active=True,
        )
        
        self.tenants[tenant_id] = tenant
        self.api_keys[api_key.id] = api_key
        self.api_key_index[key_value] = api_key.id


store = InMemoryStore()


class AuthService:
    """Authentication service."""
    
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password."""
        return pwd_context.hash(password)
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a password."""
        return pwd_context.verify(plain_password, hashed_password)
    
    @staticmethod
    def create_api_key(name: str, tenant_id: str) -> tuple[APIKey, str]:
        """Create a new API key."""
        key_value = f"cs_{secrets.token_urlsafe(32)}"
        
        api_key = APIKey(
            id=str(uuid.uuid4()),
            key=key_value,
            tenant_id=tenant_id,
            name=name,
            created_at=datetime.utcnow(),
            is_active=True,
        )
        
        store.api_keys[api_key.id] = api_key
        store.api_key_index[key_value] = api_key.id
        
        return api_key, key_value
    
    @staticmethod
    def get_api_key(key_id: str) -> Optional[APIKey]:
        """Get an API key by ID."""
        return store.api_keys.get(key_id)
    
    @staticmethod
    def get_api_key_by_value(key_value: str) -> Optional[APIKey]:
        """Get an API key by its value."""
        key_id = store.api_key_index.get(key_value)
        if key_id:
            return store.api_keys.get(key_id)
        return None
    
    @staticmethod
    def revoke_api_key(key_id: str) -> bool:
        """Revoke an API key."""
        api_key = store.api_keys.get(key_id)
        if api_key:
            api_key.is_active = False
            del store.api_key_index[api_key.key]
            return True
        return False
    
    @staticmethod
    def list_api_keys(tenant_id: str) -> list[APIKeyResponse]:
        """List all API keys for a tenant."""
        return [
            APIKeyResponse(
                id=key.id,
                name=key.name,
                created_at=key.created_at,
                last_used=key.last_used,
                is_active=key.is_active,
            )
            for key in store.api_keys.values()
            if key.tenant_id == tenant_id
        ]
    
    @staticmethod
    def create_tenant(email: str, name: str) -> Tenant:
        """Create a new tenant."""
        tenant = Tenant(
            id=str(uuid.uuid4()),
            name=name,
            email=email,
            created_at=datetime.utcnow(),
            is_active=True,
        )
        store.tenants[tenant.id] = tenant
        return tenant
    
    @staticmethod
    def get_tenant(tenant_id: str) -> Optional[Tenant]:
        """Get a tenant by ID."""
        return store.tenants.get(tenant_id)


auth_service = AuthService()


def get_current_tenant_id(authorization: str) -> Optional[str]:
    """Extract and validate tenant ID from Authorization header."""
    if not authorization:
        return None
    
    scheme, _, credentials = authorization.partition(" ")
    if scheme.lower() != "bearer":
        return None
    
    api_key = auth_service.get_api_key_by_value(credentials)
    if not api_key or not api_key.is_active:
        return None
    
    # Update last used
    api_key.last_used = datetime.utcnow()
    
    return api_key.tenant_id