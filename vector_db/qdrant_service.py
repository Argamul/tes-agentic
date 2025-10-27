import os
import uuid
from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
import numpy as np
import logging

logger = logging.getLogger(__name__)


class QdrantVectorService:
    """
    Service for managing vector search with Qdrant.
    Uses an injected `EmbeddingService` to embed text and queries.
    """

    def __init__(self):
        self.client = QdrantClient(
            url=os.getenv("QDRANT_URL", "http://localhost:6333"),
            api_key=os.getenv("QDRANT_API_KEY") or None,
        )
        self.collection_name = os.getenv("QDRANT_COLLECTION", "documents")
        self.distance_metric = Distance.COSINE
        self.embedding_service = None  # Injected
        self._collection_ready = False

    def set_embedding_service(self, embedding_service) -> None:
        self.embedding_service = embedding_service

    async def _ensure_collection(self) -> None:
        if self._collection_ready:
            return

        if not self.embedding_service:
            raise Exception("Embedding service not initialized")

        try:
            # Try to get existing collection
            existing = self.client.get_collection(self.collection_name)
            if existing:
                self._collection_ready = True
                return
        except Exception:
            pass

        # Create collection with correct vector size
        vector_size = await self.embedding_service.get_embedding_dimension()
        self.client.recreate_collection(
            collection_name=self.collection_name,
            vectors_config=VectorParams(size=vector_size, distance=self.distance_metric),
        )
        self._collection_ready = True

    async def add_document(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        if not self.embedding_service:
            raise Exception("Embedding service not initialized")
        await self._ensure_collection()

        point_id = str(uuid.uuid4())
        embedding = await self.embedding_service.generate_embedding(text)

        payload = metadata.copy() if metadata else {}
        payload.update({
            "text": text,
        })

        self.client.upsert(
            collection_name=self.collection_name,
            points=[
                PointStruct(id=point_id, vector=np.asarray(embedding, dtype=np.float32).tolist(), payload=payload)
            ],
        )
        return point_id

    async def add_documents_batch(self, texts: List[str], metadata_list: Optional[List[Dict[str, Any]]] = None) -> List[str]:
        if not self.embedding_service:
            raise Exception("Embedding service not initialized")
        await self._ensure_collection()

        if metadata_list is None:
            metadata_list = [{} for _ in texts]

        embeddings = await self.embedding_service.generate_batch_embeddings(texts)
        ids: List[str] = [str(uuid.uuid4()) for _ in texts]

        points = []
        for idx, text in enumerate(texts):
            payload = metadata_list[idx].copy()
            payload.update({"text": text})
            vector = np.asarray(embeddings[idx], dtype=np.float32).tolist()
            points.append(PointStruct(id=ids[idx], vector=vector, payload=payload))

        self.client.upsert(collection_name=self.collection_name, points=points)
        return ids

    async def search(self, query: str, top_k: int = 5, filter_metadata: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        if not self.embedding_service:
            raise Exception("Embedding service not initialized")
        await self._ensure_collection()

        query_embedding = await self.embedding_service.generate_embedding(query)

        qdrant_filter = None
        if filter_metadata:
            conditions = []
            for key, value in filter_metadata.items():
                conditions.append(FieldCondition(key=key, match=MatchValue(value=value)))
            if conditions:
                qdrant_filter = Filter(must=conditions)

        results = self.client.search(
            collection_name=self.collection_name,
            query_vector=np.asarray(query_embedding, dtype=np.float32).tolist(),
            limit=top_k,
            query_filter=qdrant_filter,
            with_payload=True,
        )

        formatted: List[Dict[str, Any]] = []
        for r in results:
            payload = (r.payload or {}).copy()
            text = payload.pop("text", "")
            formatted.append({
                "id": str(r.id),
                "document": text,
                "metadata": payload,
                "score": float(r.score),
            })
        return formatted





