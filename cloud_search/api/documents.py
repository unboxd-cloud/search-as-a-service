"""Documents API routes."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Header

from cloud_search.models import (
    DocumentAdd,
    DocumentAddResponse,
    BulkDocumentAdd,
    BulkDocumentAddResponse,
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


@router.post("/indexes/{index_name}/documents", response_model=DocumentAddResponse)
async def add_document(
    index_name: str,
    request: DocumentAdd,
    authorization: Optional[str] = Header(None),
):
    """Add a single document to an index."""
    tenant_id = get_tenant_id_or_fail(authorization)
    
    try:
        result = opensearch_client.index_document(
            tenant_id=tenant_id,
            index_name=index_name,
            document=request.document,
            doc_id=request.id,
        )
        
        return DocumentAddResponse(
            _id=result["_id"],
            status=result["status"],
            result=result["result"],
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/indexes/{index_name}/documents/_bulk", response_model=BulkDocumentAddResponse)
async def bulk_add_documents(
    index_name: str,
    request: BulkDocumentAdd,
    authorization: Optional[str] = Header(None),
):
    """Bulk add documents to an index."""
    tenant_id = get_tenant_id_or_fail(authorization)
    
    try:
        result = opensearch_client.bulk_index(
            tenant_id=tenant_id,
            index_name=index_name,
            documents=request.documents,
        )
        
        return BulkDocumentAddResponse(
            items=[
                DocumentAddResponse(
                    _id=item["_id"],
                    status=item["status"],
                    result=item["result"],
                )
                for item in result["items"]
            ],
            errors=result["errors"],
            took=result["took"],
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/indexes/{index_name}/documents/{doc_id}")
async def delete_document(
    index_name: str,
    doc_id: str,
    authorization: Optional[str] = Header(None),
):
    """Delete a document from an index."""
    tenant_id = get_tenant_id_or_fail(authorization)
    
    try:
        result = opensearch_client.delete_document(tenant_id, index_name, doc_id)
        if not result:
            raise HTTPException(status_code=404, detail="Document not found")
        return {"status": "deleted"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/indexes/{index_name}/documents/{doc_id}")
async def update_document(
    index_name: str,
    doc_id: str,
    request: dict,
    authorization: Optional[str] = Header(None),
):
    """Update a document in an index."""
    tenant_id = get_tenant_id_or_fail(authorization)
    
    try:
        result = opensearch_client.update_document(
            tenant_id=tenant_id,
            index_name=index_name,
            doc_id=doc_id,
            document=request,
        )
        return {"_id": result["_id"], "result": result["result"]}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))