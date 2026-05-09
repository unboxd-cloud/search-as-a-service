# Cloud Search as a Service - Agent Knowledge

## Overview
A multi-tenant search-as-a-service platform powered by OpenSearch.

## Key Files
- `cloud_search/main.py` - FastAPI application
- `cloud_search/services/opensearch.py` - OpenSearch client with in-memory fallback
- `cloud_search/services/auth.py` - API key authentication
- `cloud_search/api/` - REST endpoints (indexes, documents, search, auth, health)

## Commands
```bash
cd /workspace/project/cloud-search
uv sync                # Install dependencies
PORT=12000 uv run uvicorn cloud_search.main:app --host 0.0.0.0 --port 12000
```

## API Quick Start
```bash
# Register tenant
curl -X POST "http://localhost:12000/api/v1/auth/register?email=test@example.com"

# Use the returned api_key for subsequent requests
curl -X POST "http://localhost:12000/api/v1/indexes/products/documents" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"document": {"title": "iPhone 15 Pro", "price": 999}}'

curl -X POST "http://localhost:12000/api/v1/indexes/products/_search" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query": {"match": {"title": "iPhone"}}}'
```

## Testing
- Server runs on port 12000
- Health check: `curl http://localhost:12000/health`
- Uses in-memory search when OpenSearch unavailable