import os
from typing import List, Dict, Any, Optional
from elasticsearch import Elasticsearch
from elasticsearch.exceptions import NotFoundError
import logging

logger = logging.getLogger(__name__)


class ElasticBM25Service:
    """
    Service that wraps ElasticSearch for BM25 keyword search.
    Assumes an index with mappings where `text` field is analyzed.
    """

    def __init__(self):
        es_host = os.getenv("ELASTIC_URL", "http://localhost:9200")
        es_api_key = os.getenv("ELASTIC_API_KEY")
        if es_api_key:
            self.client = Elasticsearch(es_host, api_key=es_api_key)
        else:
            self.client = Elasticsearch(es_host)

        self.index_name = os.getenv("ELASTIC_INDEX", "documents")

    def ensure_index(self) -> None:
        if self.client.indices.exists(index=self.index_name):
            return
        self.client.indices.create(
            index=self.index_name,
            settings={
                "analysis": {
                    "analyzer": {
                        "default": {"type": "standard"}
                    }
                }
            },
            mappings={
                "properties": {
                    "text": {"type": "text"},
                    "metadata": {"type": "object", "enabled": True},
                }
            },
        )

    def add_document(self, text: str, metadata: Optional[Dict[str, Any]] = None, doc_id: Optional[str] = None) -> str:
        self.ensure_index()
        body = {"text": text, "metadata": metadata or {}}
        result = self.client.index(index=self.index_name, id=doc_id, document=body, refresh=True)
        return result.get("_id")

    def add_documents_batch(self, texts: List[str], metadatas: Optional[List[Dict[str, Any]]] = None) -> List[str]:
        self.ensure_index()
        ids: List[str] = []
        for idx, text in enumerate(texts):
            md = (metadatas[idx] if metadatas and idx < len(metadatas) else {})
            body = {"text": text, "metadata": md}
            result = self.client.index(index=self.index_name, document=body, refresh=(idx == len(texts) - 1))
            ids.append(result.get("_id"))
        return ids

    def search(self, query: str, top_k: int = 5, filter_metadata: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        self.ensure_index()
        must_clauses: List[Dict[str, Any]] = [{"match": {"text": query}}]
        if filter_metadata:
            for key, value in filter_metadata.items():
                must_clauses.append({"term": {f"metadata.{key}": value}})

        query_body = {
            "bool": {
                "must": must_clauses
            }
        }
        response = self.client.search(index=self.index_name, query=query_body, size=top_k)
        hits = response.get("hits", {}).get("hits", [])
        results: List[Dict[str, Any]] = []
        for h in hits:
            source = h.get("_source", {})
            results.append({
                "id": h.get("_id"),
                "document": source.get("text", ""),
                "metadata": source.get("metadata", {}),
                "score": float(h.get("_score", 0.0)),
            })
        return results

    def delete(self, doc_id: str) -> bool:
        try:
            self.client.delete(index=self.index_name, id=doc_id, refresh=True)
            return True
        except NotFoundError:
            return False


