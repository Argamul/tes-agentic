from typing import List, Dict, Any, Optional, Tuple
import math
import os
from cache.redis_cache import make_cache_key, cache_get_json, cache_set_json


def _min_max_normalize(scores: List[float]) -> List[float]:
    if not scores:
        return []
    min_s, max_s = min(scores), max(scores)
    if math.isclose(min_s, max_s):
        return [1.0 for _ in scores]
    return [(s - min_s) / (max_s - min_s) for s in scores]


class HybridRetriever:
    """
    Combines BM25 (ElasticSearch) results with semantic vector results (Qdrant) and merges them.
    """

    def __init__(self, bm25_service, vector_service, alpha: float = 0.5):
        """
        Args:
            bm25_service: Instance providing `search(query, top_k, filter_metadata)`
            vector_service: Instance providing `search(query, top_k, filter_metadata)`
            alpha: Weight for semantic score in [0,1]. Final = alpha*sem + (1-alpha)*bm25
        """
        self.bm25_service = bm25_service
        self.vector_service = vector_service
        self.alpha = alpha

    async def search(self, query: str, top_k: int = 10, filter_metadata: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        # Cache lookup (optional)
        if os.getenv("REDIS_CACHE_ENABLED", "true").lower() in {"1", "true", "yes"}:
            cache_key = make_cache_key("search:hybrid", {"q": query, "k": top_k, "a": self.alpha, "f": filter_metadata or {}})
            cached = await cache_get_json(cache_key)
            if cached is not None:
                return cached

        # Fetch results in parallel if upstream supports async; our bm25 is sync so we call directly
        bm25_results = self.bm25_service.search(query, top_k=top_k, filter_metadata=filter_metadata)
        vector_results = await self.vector_service.search(query, top_k=top_k, filter_metadata=filter_metadata)

        # Normalize scores to 0..1
        bm25_scores = _min_max_normalize([r.get("score", 0.0) for r in bm25_results])
        vector_scores = _min_max_normalize([r.get("score", 0.0) for r in vector_results])

        # Index by a stable key; prefer explicit id; if missing, use document text hash
        def make_key(r: Dict[str, Any]) -> str:
            if r.get("id"):
                return str(r["id"])  # ES ids are string, Qdrant ids may be int/uuid
            return str(hash(r.get("document", "")))

        bm25_map = {make_key(r): (r, bm25_scores[i]) for i, r in enumerate(bm25_results)}
        vector_map = {make_key(r): (r, vector_scores[i]) for i, r in enumerate(vector_results)}

        merged: Dict[str, Dict[str, Any]] = {}
        for key, (item, norm_score) in bm25_map.items():
            merged[key] = {
                "id": item.get("id"),
                "document": item.get("document"),
                "metadata": item.get("metadata", {}),
                "bm25": norm_score,
                "semantic": 0.0,
            }

        for key, (item, norm_score) in vector_map.items():
            if key in merged:
                merged[key]["semantic"] = max(merged[key]["semantic"], norm_score)
                # Prefer richer metadata or text if present
                if item.get("metadata"):
                    merged[key]["metadata"] = item.get("metadata")
                if item.get("document") and len(item.get("document", "")) > len(merged[key]["document"] or ""):
                    merged[key]["document"] = item.get("document")
            else:
                merged[key] = {
                    "id": item.get("id"),
                    "document": item.get("document"),
                    "metadata": item.get("metadata", {}),
                    "bm25": 0.0,
                    "semantic": norm_score,
                }

        # Compute final score and rank
        results: List[Tuple[str, Dict[str, Any]]] = []
        for key, item in merged.items():
            final_score = self.alpha * item["semantic"] + (1.0 - self.alpha) * item["bm25"]
            out = {
                "id": item.get("id"),
                "document": item.get("document"),
                "metadata": item.get("metadata", {}),
                "bm25_score": item["bm25"],
                "semantic_score": item["semantic"],
                "score": final_score,
            }
            results.append((key, out))

        results.sort(key=lambda kv: kv[1]["score"], reverse=True)
        ranked = [r for _, r in results[:top_k]]

        if os.getenv("REDIS_CACHE_ENABLED", "true").lower() in {"1", "true", "yes"}:
            try:
                await cache_set_json(cache_key, ranked)
            except Exception:
                pass
        return ranked


