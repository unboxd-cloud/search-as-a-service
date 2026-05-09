"""OpenSearch client service with in-memory fallback."""
import os
import uuid
from typing import Any, Optional

from pydantic import BaseModel

from opensearchpy import OpenSearch
from opensearchpy.exceptions import NotFoundError


class Settings(BaseModel):
    """Application settings."""
    opensearch_host: str = os.getenv("OPENSEARCH_HOST", "localhost")
    opensearch_port: int = int(os.getenv("OPENSEARCH_PORT", "9200"))
    opensearch_user: str = os.getenv("OPENSEARCH_USER", "admin")
    opensearch_password: str = os.getenv("OPENSEARCH_PASSWORD", "admin")
    opensearch_use_ssl: bool = os.getenv("OPENSEARCH_USE_SSL", "false").lower() == "true"

    class Config:
        extra = "allow"


settings = Settings()


class InMemorySearchIndex:
    """In-memory search index for testing/demo."""

    def __init__(self, name: str):
        self.name = name
        self.documents: dict[str, dict[str, Any]] = {}
        self.settings: dict[str, Any] = {}
        self.mapping: dict[str, Any] = {}

    def add_document(self, doc_id: Optional[str], document: dict[str, Any]) -> str:
        """Add a document."""
        if doc_id is None:
            doc_id = str(uuid.uuid4())
        self.documents[doc_id] = document
        return doc_id

    def search(self, query: dict, from_: int = 0, size: int = 10) -> dict[str, Any]:
        """Search documents (simple implementation)."""
        matches = []
        query_text = query.get("match", {}).get("text") if "match" in query else None
        query_multi = query.get("multi_match", {}).get("query") if "multi_match" in query else None
        query_match_all = "match_all" in query

        for doc_id, doc in self.documents.items():
            score = 0.0
            if query_text:
                text = doc.get("text", "")
                if isinstance(text, str) and query_text.lower() in text.lower():
                    score = 1.0
            elif query_multi:
                for field, value in doc.items():
                    if isinstance(value, str) and query_multi.lower() in value.lower():
                        score = 1.0
            elif query_match_all:
                score = 1.0
            else:
                score = 1.0

            if score > 0:
                matches.append({
                    "_id": doc_id,
                    "_score": score,
                    "_source": doc,
                })

        matches.sort(key=lambda x: x["_score"], reverse=True)

        return {
            "hits": {
                "total": {"value": len(matches)},
                "hits": matches[from_:from_ + size],
            },
            "took": 1,
        }


class InMemorySearchClient:
    """In-memory OpenSearch-compatible client."""

    def __init__(self):
        self.indexes: dict[str, InMemorySearchIndex] = {}

    def create_index(
        self,
        index: str,
        body: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        idx = InMemorySearchIndex(index)
        if body:
            if "settings" in body:
                idx.settings = body["settings"]
            if "mappings" in body:
                idx.mapping = body["mappings"]
        self.indexes[index] = idx
        return {"acknowledged": True}

    def delete_index(self, index: str) -> dict[str, Any]:
        if index in self.indexes:
            del self.indexes[index]
        return {"acknowledged": True}

    def indices(self) -> "InMemorySearchClient":
        return self

    def get(self, index: str) -> dict[str, Any]:
        if index not in self.indexes:
            raise NotFoundError(404, "index not found")
        idx = self.indexes[index]
        return {index: {"mappings": idx.mapping, "settings": idx.settings}}

    def stats(self, index: Optional[str] = None) -> dict[str, Any]:
        if index:
            idx = self.indexes.get(index)
            if not idx:
                return {"_all": {"primaries": {"docs": {"count": 0}}}}
            return {"_all": {"primaries": {"docs": {"count": len(idx.documents)}}}}
        return {"_all": {"primaries": {"docs": {"count": 0}}}}

    def index(
        self,
        index: str,
        body: Optional[dict[str, Any]] = None,
        id: Optional[str] = None,
        refresh: bool = False,
    ) -> dict[str, Any]:
        if index not in self.indexes:
            self.create_index(index)
        doc_id = self.indexes[index].add_document(id, body or {})
        return {"_id": doc_id, "result": "created", "_index": index}

    def bulk(self, body: list, refresh: bool = False) -> dict[str, Any]:
        items = []
        i = 0
        while i < len(body):
            action = body[i]
            i += 1
            if i >= len(body):
                break
            doc = body[i]
            i += 1
            op = list(action.keys())[0]
            idx_name = action[op].get("_index", "unknown")
            doc_id = action[op].get("_id")
            if idx_name in self.indexes:
                actual_id = self.indexes[idx_name].add_document(doc_id, doc)
            else:
                idx = InMemorySearchIndex(idx_name)
                actual_id = idx.add_document(doc_id, doc)
                self.indexes[idx_name] = idx
            items.append({op: {"_id": actual_id, "result": "created"}})
        return {"items": items, "took": len(items)}

    def search(
        self,
        index: str,
        body: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        if index not in self.indexes:
            return {"hits": {"total": {"value": 0}, "hits": []}}
        query = body.get("query", {"match_all": {}}) if body else {"match_all": {}}
        from_ = body.get("from", 0) if body else 0
        size = body.get("size", 10) if body else 10
        return self.indexes[index].search(query, from_, size)

    def delete(
        self,
        index: str,
        id: str,
        refresh: bool = False,
    ) -> dict[str, Any]:
        if index in self.indexes and id in self.indexes[index].documents:
            del self.indexes[index].documents[id]
            return {"result": "deleted"}
        raise NotFoundError(404, "document not found")

    def update(
        self,
        index: str,
        id: str,
        body: Optional[dict[str, Any]] = None,
        refresh: bool = False,
    ) -> dict[str, Any]:
        if index not in self.indexes:
            raise NotFoundError(404, "index not found")
        idx = self.indexes[index]
        if body and "doc" in body:
            if id in idx.documents:
                idx.documents[id].update(body["doc"])
            else:
                idx.documents[id] = body["doc"]
        return {"_id": id, "result": "updated"}

    def cluster(self) -> "InMemorySearchClient":
        return self

    def health(self) -> dict[str, Any]:
        return {"status": "green", "cluster_name": "demo"}


# Global in-memory client
in_memory_client = InMemorySearchClient()


class OpenSearchClient:
    """OpenSearch client wrapper with in-memory fallback."""

    def __init__(self):
        self.client: Any = None
        self._connected = False

    def connect(self) -> bool:
        """Try to connect to OpenSearch."""
        try:
            self.client = OpenSearch(
                hosts=[{"host": settings.opensearch_host, "port": settings.opensearch_port}],
                http_auth=(settings.opensearch_user, settings.opensearch_password),
                use_ssl=settings.opensearch_use_ssl,
                verify_certs=False,
                ssl_show_warn=False,
            )
            self.client.cluster.health()
            self._connected = True
            return True
        except Exception as e:
            print(f"OpenSearch not available: {e}. Using in-memory store.")
            self.client = in_memory_client
            self._connected = True
            return False

    @property
    def is_connected(self) -> bool:
        return self._connected

    def _get_index_name(self, tenant_id: str, index_name: str) -> str:
        return f"{tenant_id}_{index_name}"

    def create_index(
        self,
        tenant_id: str,
        index_name: str,
        settings: Optional[dict[str, Any]] = None,
        mapping: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        full_name = self._get_index_name(tenant_id, index_name)
        body = {}
        if settings:
            body["settings"] = settings
        if mapping:
            body["mappings"] = mapping
        self.client.indices().create(index=full_name, body=body)
        return {"name": index_name, "full_name": full_name, "settings": settings, "mapping": mapping}

    def delete_index(self, tenant_id: str, index_name: str) -> bool:
        full_name = self._get_index_name(tenant_id, index_name)
        try:
            self.client.indices().delete_index(full_name)
            return True
        except NotFoundError:
            return False

    def list_indexes(self, tenant_id: str) -> list[dict[str, Any]]:
        prefix = f"{tenant_id}_"
        result = []
        for name in self.client.indexes:
            if name.startswith(prefix):
                idx = self.client.indexes[name]
                result.append({
                    "name": name[len(prefix):],
                    "health": "green",
                    "status": "open",
                    "document_count": len(idx.documents),
                    "store_size": "0b",
                })
        return result

    def get_index(self, tenant_id: str, index_name: str) -> Optional[dict[str, Any]]:
        full_name = self._get_index_name(tenant_id, index_name)
        try:
            info = self.client.indices().get(full_name)[full_name]
            stats = self.client.indices().stats(full_name)
            return {"name": index_name, "settings": info.get("settings", {}), "mappings": info.get("mappings", {}), "document_count": stats["_all"]["primaries"]["docs"]["count"]}
        except NotFoundError:
            return None
        except Exception:
            return None

    def index_document(
        self,
        tenant_id: str,
        index_name: str,
        document: dict[str, Any],
        doc_id: Optional[str] = None,
    ) -> dict[str, Any]:
        full_name = self._get_index_name(tenant_id, index_name)
        response = self.client.index(index=full_name, body=document, id=doc_id, refresh=True)
        return {"_id": response["_id"], "status": "created" if response["result"] == "created" else "updated", "result": response["result"]}

    def bulk_index(
        self,
        tenant_id: str,
        index_name: str,
        documents: list[dict[str, Any]],
    ) -> dict[str, Any]:
        full_name = self._get_index_name(tenant_id, index_name)
        actions = []
        for doc in documents:
            doc_id = doc.get("id")
            actions.append({"index": {"_index": full_name, "_id": doc_id}})
            actions.append(doc)
        response = self.client.bulk(body=actions, refresh=True)
        items = []
        errors = False
        for item in response["items"]:
            op_type = list(item.keys())[0]
            items.append({"_id": item[op_type].get("_id"), "status": op_type, "result": item[op_type].get("result")})
            if item[op_type].get("error"):
                errors = True
        return {"items": items, "errors": errors, "took": response["took"]}

    def search(
        self,
        tenant_id: str,
        index_name: str,
        query: dict[str, Any],
        from_: int = 0,
        size: int = 10,
    ) -> dict[str, Any]:
        full_name = self._get_index_name(tenant_id, index_name)
        body = {"query": query, "from": from_, "size": size}
        return self.client.search(index=full_name, body=body)

    def delete_document(self, tenant_id: str, index_name: str, doc_id: str) -> bool:
        full_name = self._get_index_name(tenant_id, index_name)
        try:
            self.client.delete(index=full_name, id=doc_id, refresh=True)
            return True
        except NotFoundError:
            return False

    def update_document(
        self,
        tenant_id: str,
        index_name: str,
        doc_id: str,
        document: dict[str, Any],
    ) -> dict[str, Any]:
        full_name = self._get_index_name(tenant_id, index_name)
        response = self.client.update(index=full_name, id=doc_id, body={"doc": document, "doc_as_upsert": True}, refresh=True)
        return {"_id": response["_id"], "result": response["result"]}

    def get_cluster_health(self) -> dict[str, Any]:
        return self.client.cluster().health()


# Global client instance
opensearch_client = OpenSearchClient()
opensearch_client.connect()