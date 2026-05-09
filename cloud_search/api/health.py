"""Health API routes."""
from fastapi import APIRouter, Depends, HTTPException, Header
from typing import Optional

from cloud_search.models import HealthResponse
from cloud_search.services.auth import get_current_tenant_id
from cloud_search.services.opensearch import opensearch_client


router = APIRouter()


@router.get("", response_model=HealthResponse)
async def health_check(authorization: Optional[str] = Header(None)):
    """Health check endpoint."""
    oc = opensearch_client
    
    if oc.is_connected:
        health = oc.get_cluster_health()
        return HealthResponse(
            status="healthy",
            opensearch=health.get("status", "unknown"),
            version=health.get("cluster_name"),
        )
    else:
        # Try to reconnect
        if oc.connect():
            health = oc.get_cluster_health()
            return HealthResponse(
                status="healthy",
                opensearch=health.get("status", "unknown"),
                version=health.get("cluster_name"),
            )
        
        return HealthResponse(
            status="degraded",
            opensearch="disconnected",
            version=None,
        )