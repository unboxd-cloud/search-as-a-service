"""Search API routes."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Header

from cloud_search.models import SearchRequest, SearchResponse
from cloud_search.services.auth import get_current_tenant_id
from cloud_search.services.opensearch import opensearch_client


router = APIRouter()


def get_tenant_id_or_fail(authorization: Optional[str]) -> str:
    """Get tenant ID or raise 401."""
    tenant_id = get_current_tenant_id(authorization or "")
    if not tenant_id:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    return tenant_id


@router.post("/indexes/{index_name}/_search", response_model=SearchResponse)
async def search_index(
    index_name: str,
    request: SearchRequest,
    authorization: Optional[str] = Header(None),
):
    """Search documents in an index."""
    tenant_id = get_tenant_id_or_fail(authorization)
    
    try:
        result = opensearch_client.search(
            tenant_id=tenant_id,
            index_name=index_name,
            query=request.query,
            from_=request.from_ or 0,
            size=request.size,
        )
        
        return SearchResponse(
            took=result.get("took", 0),
            timed_out=result.get("timed_out", False),
            hits=result.get("hits", {}),
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))