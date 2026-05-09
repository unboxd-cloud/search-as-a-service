"""Auth API routes."""
import secrets
from typing import Optional

from fastapi import APIRouter, HTTPException, Header

from cloud_search.services.auth import auth_service


router = APIRouter()


@router.post("/auth/register")
async def register(email: str, name: str = "Demo"):
    """Register a new tenant and get API key."""
    tenant = auth_service.create_tenant(email, name)
    api_key, key_value = auth_service.create_api_key("default", tenant.id)
    return {
        "tenant_id": tenant.id,
        "api_key": key_value,
        "name": name,
    }


@router.get("/auth/key")
async def get_api_key(authorization: Optional[str] = Header(None)):
    """Get current API key info."""
    tenant_id = get_current_tenant_id_auth(authorization)
    if not tenant_id:
        raise HTTPException(status_code=401, detail="Invalid API key")
    keys = auth_service.list_api_keys(tenant_id)
    return {"keys": keys}


def get_current_tenant_id_auth(auth: str) -> Optional[str]:
    """Extract tenant ID from Authorization header."""
    if not auth:
        return None
    scheme, _, creds = auth.partition(" ")
    if scheme.lower() != "bearer":
        return None
    api_key = auth_service.get_api_key_by_value(creds)
    if not api_key or not api_key.is_active:
        return None
    return api_key.tenant_id