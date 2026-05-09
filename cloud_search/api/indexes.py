"""Indexes API routes."""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Header

from cloud_search.models import (
    IndexCreate,
    IndexResponse,
    IndexListResponse,
    IndexSettings,
)
from cloud_search.services.auth import get_current_tenant_id
from cloud_search.services.opensearch import opensearch_client


router = APIRouter()


def get_tenant_id_or_fail(authorization: Optional[str]) -> str:
    """Get tenant ID or raise 401."""
    tenant_id = get_current_tenant_id(authorization or "")
    if not tenant_id:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    return tenant_id


@router.post("/indexes", response_model=IndexResponse, status_code=201)
async def create_index(
    index: IndexCreate,
    authorization: Optional[str] = Header(None),
):
    """Create a new index."""
    tenant_id = get_tenant_id_or_fail(authorization)
    
    try:
        settings_dict = None
        if index.settings:
            settings_dict = {
                "index": {
                    "number_of_shards": index.settings.number_of_shards,
                    "number_of_replicas": index.settings.number_of_replicas,
                    "refresh_interval": index.settings.refresh_interval,
                }
            }
        
        mapping_dict = None
        if index.mapping:
            mapping_dict = {"properties": {k: v.model_dump() for k, v in index.mapping.properties.items()}}
        
        result = opensearch_client.create_index(
            tenant_id=tenant_id,
            index_name=index.name,
            settings=settings_dict,
            mapping=mapping_dict,
        )
        
        return IndexResponse(
            name=result["name"],
            settings=result.get("settings"),
            mapping=result.get("mapping"),
            document_count=0,
            created_at=datetime.utcnow(),
            status="active",
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/indexes", response_model=IndexListResponse)
async def list_indexes(
    authorization: Optional[str] = Header(None),
):
    """List all indexes for the tenant."""
    tenant_id = get_tenant_id_or_fail(authorization)
    
    try:
        indexes = opensearch_client.list_indexes(tenant_id)
        
        return IndexListResponse(
            indexes=[
                IndexResponse(
                    name=idx["name"],
                    settings={"index": idx},
                    mapping=None,
                    document_count=idx.get("document_count", 0),
                    created_at=datetime.utcnow(),
                    status=idx.get("status", "active"),
                )
                for idx in indexes
            ],
            total=len(indexes),
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/indexes/{index_name}", response_model=IndexResponse)
async def get_index(
    index_name: str,
    authorization: Optional[str] = Header(None),
):
    """Get index details."""
    tenant_id = get_tenant_id_or_fail(authorization)
    
    try:
        index = opensearch_client.get_index(tenant_id, index_name)
        if not index:
            raise HTTPException(status_code=404, detail="Index not found")
        
        return IndexResponse(
            name=index["name"],
            settings=index.get("settings"),
            mapping=index.get("mappings"),
            document_count=index.get("document_count", 0),
            created_at=datetime.utcnow(),
            status="active",
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/indexes/{index_name}", status_code=204)
async def delete_index(
    index_name: str,
    authorization: Optional[str] = Header(None),
):
    """Delete an index."""
    tenant_id = get_tenant_id_or_fail(authorization)
    
    try:
        result = opensearch_client.delete_index(tenant_id, index_name)
        if not result:
            raise HTTPException(status_code=404, detail="Index not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))