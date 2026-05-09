"""
Cloud Search as a Service - Main Application
"""
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from cloud_search.api import indexes, documents, search, health, auth
from cloud_search.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup: client is already connected during import
    # Just verify
    try:
        from cloud_search.services.opensearch import opensearch_client
        if opensearch_client.is_connected:
            health = opensearch_client.get_cluster_health()
            print(f"OpenSearch cluster: {health.get('status')}")
    except Exception as e:
        print(f"Warning during startup: {e}")
    yield
    # Shutdown
    print("Shutting down...")


app = FastAPI(
    title="Cloud Search API",
    description="Search-as-a-Service powered by OpenSearch",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    import time
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


# Include routers
app.include_router(health.router, prefix="/health", tags=["Health"])
app.include_router(indexes.router, prefix="/api/v1", tags=["Indexes"])
app.include_router(documents.router, prefix="/api/v1", tags=["Documents"])
app.include_router(search.router, prefix="/api/v1", tags=["Search"])
app.include_router(auth.router, prefix="/api/v1", tags=["Auth"])


@app.get("/")
async def root():
    return {
        "name": "Cloud Search API",
        "version": "1.0.0",
        "docs": "/docs",
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "12000"))
    uvicorn.run(
        "cloud_search.main:app",
        host="0.0.0.0",
        port=port,
        reload=True,
    )