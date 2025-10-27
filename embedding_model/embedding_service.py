import os
import asyncio
from typing import List, Optional, Union, Dict
import numpy as np
from sentence_transformers import SentenceTransformer
import torch
import logging
from cache.redis_cache import (
    make_cache_key,
    cache_get_json,
    cache_set_json,
)

logger = logging.getLogger(__name__)

class EmbeddingService:
    """
    Service for generating text embeddings using various embedding models.
    Supports both single and batch embedding generation.
    """
    
    def __init__(self):
        self.models = {}
        self.default_model = "all-MiniLM-L6-v2"
        self.available_models = {
            "all-MiniLM-L6-v2": "Sentence Transformers - MiniLM",
            "all-mpnet-base-v2": "Sentence Transformers - MPNet",
            "text-embedding-ada-002": "OpenAI Ada Embeddings"
        }
    
    async def _load_model(self, model_name: str) -> SentenceTransformer:
        """
        Load a sentence transformer model asynchronously.
        
        Args:
            model_name: Name of the model to load
            
        Returns:
            Loaded SentenceTransformer model
        """
        if model_name not in self.models:
            try:
                logger.info(f"Loading model: {model_name}")
                self.models[model_name] = SentenceTransformer(model_name)
                logger.info(f"Model {model_name} loaded successfully")
            except Exception as e:
                logger.error(f"Error loading model {model_name}: {str(e)}")
                raise Exception(f"Failed to load model {model_name}: {str(e)}")
        
        return self.models[model_name]
    
    async def generate_embedding(self, text: str, model: Optional[str] = None) -> np.ndarray:
        """
        Generate embedding for a single text.
        
        Args:
            text: Input text to embed
            model: Model name to use (defaults to all-MiniLM-L6-v2)
            
        Returns:
            Numpy array containing the embedding
        """
        try:
            model_name = model or self.default_model
            
            # Redis cache (optional)
            import os
            if os.getenv("REDIS_CACHE_ENABLED", "true").lower() in {"1", "true", "yes"}:
                cache_key = make_cache_key("emb:single", {"text": text, "model": model_name})
                cached = await cache_get_json(cache_key)
                if cached is not None:
                    return np.array(cached)

            if model_name == "text-embedding-ada-002":
                return await self._generate_openai_embedding(text)
            
            # Use sentence transformers
            model_instance = await self._load_model(model_name)
            
            # Run embedding generation in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            embedding = await loop.run_in_executor(
                None, 
                model_instance.encode, 
                text
            )
            
            # Cache result
            if os.getenv("REDIS_CACHE_ENABLED", "true").lower() in {"1", "true", "yes"}:
                try:
                    await cache_set_json(cache_key, embedding.tolist())
                except Exception:
                    pass
            return embedding
            
        except Exception as e:
            logger.error(f"Error generating embedding: {str(e)}")
            raise Exception(f"Embedding generation failed: {str(e)}")
    
    async def generate_batch_embeddings(self, texts: List[str], model: Optional[str] = None) -> List[np.ndarray]:
        """
        Generate embeddings for multiple texts in batch.
        
        Args:
            texts: List of texts to embed
            model: Model name to use (defaults to all-MiniLM-L6-v2)
            
        Returns:
            List of numpy arrays containing embeddings
        """
        try:
            model_name = model or self.default_model
            
            # Prepare cache lookup
            import os
            use_cache = os.getenv("REDIS_CACHE_ENABLED", "true").lower() in {"1", "true", "yes"}
            cached_results: Dict[int, np.ndarray] = {}
            missing_indices: List[int] = []
            cache_keys: List[str] = []
            if use_cache:
                for idx, t in enumerate(texts):
                    key = make_cache_key("emb:single", {"text": t, "model": model_name})
                    cache_keys.append(key)
                for idx, key in enumerate(cache_keys):
                    cached = await cache_get_json(key)
                    if cached is not None:
                        cached_results[idx] = np.array(cached)
                    else:
                        missing_indices.append(idx)
            else:
                # When cache disabled, compute all and return
                if model_name == "text-embedding-ada-002":
                    emb_list = await self._generate_openai_batch_embeddings(texts)
                    return emb_list
                # Sentence Transformers path, compute all
                model_instance = await self._load_model(model_name)
                loop = asyncio.get_event_loop()
                embeddings = await loop.run_in_executor(
                    None,
                    model_instance.encode,
                    texts,
                )
                return embeddings

            # If OpenAI path
            if model_name == "text-embedding-ada-002":
                if missing_indices:
                    missing_texts = [texts[i] for i in missing_indices]
                    new_embeddings = await self._generate_openai_batch_embeddings(missing_texts)
                    for i, emb in zip(missing_indices, new_embeddings):
                        if use_cache:
                            try:
                                await cache_set_json(cache_keys[i], emb.tolist())
                            except Exception:
                                pass
                        cached_results[i] = np.array(emb)
                # Assemble in original order
                return [cached_results[i] if i in cached_results else np.array([]) for i in range(len(texts))]

            # Sentence Transformers path
            model_instance = await self._load_model(model_name)
            if missing_indices:
                missing_texts = [texts[i] for i in missing_indices]
                loop = asyncio.get_event_loop()
                new_embeddings = await loop.run_in_executor(
                    None,
                    model_instance.encode,
                    missing_texts,
                )
                for i, emb in zip(missing_indices, new_embeddings):
                    if use_cache:
                        try:
                            await cache_set_json(cache_keys[i], emb.tolist())
                        except Exception:
                            pass
                    cached_results[i] = np.array(emb)
            return [cached_results[i] if i in cached_results else np.array([]) for i in range(len(texts))]
            
        except Exception as e:
            logger.error(f"Error generating batch embeddings: {str(e)}")
            raise Exception(f"Batch embedding generation failed: {str(e)}")
    
    async def _generate_openai_embedding(self, text: str) -> np.ndarray:
        """
        Generate embedding using OpenAI's API.
        
        Args:
            text: Input text to embed
            
        Returns:
            Numpy array containing the embedding
        """
        try:
            from openai import AsyncOpenAI
            
            client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            
            response = await client.embeddings.create(
                input=text,
                model="text-embedding-ada-002"
            )
            
            return np.array(response.data[0].embedding)
            
        except Exception as e:
            logger.error(f"Error generating OpenAI embedding: {str(e)}")
            raise Exception(f"OpenAI embedding generation failed: {str(e)}")
    
    async def _generate_openai_batch_embeddings(self, texts: List[str]) -> List[np.ndarray]:
        """
        Generate embeddings for multiple texts using OpenAI's API.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of numpy arrays containing embeddings
        """
        try:
            from openai import AsyncOpenAI
            
            client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            
            response = await client.embeddings.create(
                input=texts,
                model="text-embedding-ada-002"
            )
            
            return [np.array(embedding.embedding) for embedding in response.data]
            
        except Exception as e:
            logger.error(f"Error generating OpenAI batch embeddings: {str(e)}")
            raise Exception(f"OpenAI batch embedding generation failed: {str(e)}")
    
    def get_available_models(self) -> dict:
        """
        Get list of available embedding models.
        
        Returns:
            Dictionary of model names and descriptions
        """
        return self.available_models
    
    async def get_embedding_dimension(self, model: Optional[str] = None) -> int:
        """
        Get the dimension of embeddings for a specific model.
        
        Args:
            model: Model name to check
            
        Returns:
            Embedding dimension
        """
        try:
            model_name = model or self.default_model
            
            if model_name == "text-embedding-ada-002":
                return 1536  # OpenAI ada-002 dimension
            
            # For sentence transformers, get dimension from model
            model_instance = await self._load_model(model_name)
            return model_instance.get_sentence_embedding_dimension()
            
        except Exception as e:
            logger.error(f"Error getting embedding dimension: {str(e)}")
            raise Exception(f"Failed to get embedding dimension: {str(e)}")
    
    async def compute_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """
        Compute cosine similarity between two embeddings.
        
        Args:
            embedding1: First embedding
            embedding2: Second embedding
            
        Returns:
            Cosine similarity score
        """
        try:
            # Normalize embeddings
            norm1 = np.linalg.norm(embedding1)
            norm2 = np.linalg.norm(embedding2)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            # Compute cosine similarity
            similarity = np.dot(embedding1, embedding2) / (norm1 * norm2)
            return float(similarity)
            
        except Exception as e:
            logger.error(f"Error computing similarity: {str(e)}")
            raise Exception(f"Similarity computation failed: {str(e)}")
