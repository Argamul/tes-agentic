import os
import uuid
import asyncio
from typing import List, Dict, Any, Optional, Tuple
import chromadb
from chromadb.config import Settings
import numpy as np
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class VectorService:
    """
    Service for managing vector database operations including document storage,
    similarity search, and vector management using ChromaDB.
    """
    
    def __init__(self):
        self.client = chromadb.PersistentClient(
            path="./chroma_db",
            settings=Settings(
                anonymized_telemetry=False
            )
        )
        self.collection_name = "documents"
        self.collection = self._get_or_create_collection()
        self.embedding_service = None  # Will be injected from main app
    
    def _get_or_create_collection(self):
        """
        Get existing collection or create a new one.
        
        Returns:
            ChromaDB collection
        """
        try:
            # Try to get existing collection
            collection = self.client.get_collection(name=self.collection_name)
            logger.info(f"Using existing collection: {self.collection_name}")
        except:
            # Create new collection if it doesn't exist
            collection = self.client.create_collection(
                name=self.collection_name,
                metadata={"description": "Document embeddings for similarity search"}
            )
            logger.info(f"Created new collection: {self.collection_name}")
        
        return collection
    
    def set_embedding_service(self, embedding_service):
        """
        Set the embedding service for generating embeddings.
        
        Args:
            embedding_service: EmbeddingService instance
        """
        self.embedding_service = embedding_service
    
    async def add_document(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Add a document to the vector database.
        
        Args:
            text: Document text content
            metadata: Optional metadata for the document
            
        Returns:
            Document ID
        """
        try:
            if not self.embedding_service:
                raise Exception("Embedding service not initialized")
            
            # Generate document ID
            doc_id = str(uuid.uuid4())
            
            # Generate embedding
            embedding = await self.embedding_service.generate_embedding(text)
            
            # Prepare metadata
            doc_metadata = metadata or {}
            doc_metadata.update({
                "timestamp": datetime.now().isoformat(),
                "text_length": len(text)
            })
            
            # Add to collection
            self.collection.add(
                embeddings=[embedding.tolist()],
                documents=[text],
                metadatas=[doc_metadata],
                ids=[doc_id]
            )
            
            logger.info(f"Added document with ID: {doc_id}")
            return doc_id
            
        except Exception as e:
            logger.error(f"Error adding document: {str(e)}")
            raise Exception(f"Failed to add document: {str(e)}")
    
    async def add_documents_batch(self, texts: List[str], metadata_list: Optional[List[Dict[str, Any]]] = None) -> List[str]:
        """
        Add multiple documents to the vector database in batch.
        
        Args:
            texts: List of document texts
            metadata_list: Optional list of metadata dictionaries
            
        Returns:
            List of document IDs
        """
        try:
            if not self.embedding_service:
                raise Exception("Embedding service not initialized")
            
            # Generate document IDs
            doc_ids = [str(uuid.uuid4()) for _ in texts]
            
            # Generate embeddings in batch
            embeddings = await self.embedding_service.generate_batch_embeddings(texts)
            
            # Prepare metadata
            if metadata_list is None:
                metadata_list = [{} for _ in texts]
            
            for i, metadata in enumerate(metadata_list):
                metadata.update({
                    "timestamp": datetime.now().isoformat(),
                    "text_length": len(texts[i])
                })
            
            # Add to collection
            self.collection.add(
                embeddings=[emb.tolist() for emb in embeddings],
                documents=texts,
                metadatas=metadata_list,
                ids=doc_ids
            )
            
            logger.info(f"Added {len(texts)} documents in batch")
            return doc_ids
            
        except Exception as e:
            logger.error(f"Error adding documents batch: {str(e)}")
            raise Exception(f"Failed to add documents batch: {str(e)}")
    
    async def search(self, query: str, top_k: int = 5, filter_metadata: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Search for similar documents using vector similarity.
        
        Args:
            query: Search query text
            top_k: Number of top results to return
            filter_metadata: Optional metadata filter
            
        Returns:
            List of search results with documents and scores
        """
        try:
            if not self.embedding_service:
                raise Exception("Embedding service not initialized")
            
            # Generate query embedding
            query_embedding = await self.embedding_service.generate_embedding(query)
            
            # Perform search
            results = self.collection.query(
                query_embeddings=[query_embedding.tolist()],
                n_results=top_k,
                where=filter_metadata
            )
            
            # Format results
            formatted_results = []
            for i in range(len(results['documents'][0])):
                result = {
                    'id': results['ids'][0][i],
                    'document': results['documents'][0][i],
                    'metadata': results['metadatas'][0][i],
                    'score': results['distances'][0][i]
                }
                formatted_results.append(result)
            
            logger.info(f"Search completed, found {len(formatted_results)} results")
            return formatted_results
            
        except Exception as e:
            logger.error(f"Error searching documents: {str(e)}")
            raise Exception(f"Search failed: {str(e)}")
    
    async def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a specific document by ID.
        
        Args:
            doc_id: Document ID
            
        Returns:
            Document data or None if not found
        """
        try:
            results = self.collection.get(ids=[doc_id])
            
            if not results['documents']:
                return None
            
            return {
                'id': doc_id,
                'document': results['documents'][0],
                'metadata': results['metadatas'][0],
                'embedding': results['embeddings'][0] if results['embeddings'] else None
            }
            
        except Exception as e:
            logger.error(f"Error getting document {doc_id}: {str(e)}")
            raise Exception(f"Failed to get document: {str(e)}")
    
    async def update_document(self, doc_id: str, text: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Update an existing document.
        
        Args:
            doc_id: Document ID to update
            text: New document text
            metadata: Optional new metadata
            
        Returns:
            True if successful, False if document not found
        """
        try:
            if not self.embedding_service:
                raise Exception("Embedding service not initialized")
            
            # Check if document exists
            existing_doc = await self.get_document(doc_id)
            if not existing_doc:
                return False
            
            # Generate new embedding
            embedding = await self.embedding_service.generate_embedding(text)
            
            # Prepare metadata
            doc_metadata = metadata or existing_doc['metadata']
            doc_metadata.update({
                "updated_timestamp": datetime.now().isoformat(),
                "text_length": len(text)
            })
            
            # Update document
            self.collection.update(
                ids=[doc_id],
                embeddings=[embedding.tolist()],
                documents=[text],
                metadatas=[doc_metadata]
            )
            
            logger.info(f"Updated document: {doc_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating document {doc_id}: {str(e)}")
            raise Exception(f"Failed to update document: {str(e)}")
    
    async def delete_document(self, doc_id: str) -> bool:
        """
        Delete a document from the vector database.
        
        Args:
            doc_id: Document ID to delete
            
        Returns:
            True if successful, False if document not found
        """
        try:
            # Check if document exists
            existing_doc = await self.get_document(doc_id)
            if not existing_doc:
                return False
            
            # Delete document
            self.collection.delete(ids=[doc_id])
            
            logger.info(f"Deleted document: {doc_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting document {doc_id}: {str(e)}")
            raise Exception(f"Failed to delete document: {str(e)}")
    
    async def get_collection_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the vector database collection.
        
        Returns:
            Dictionary with collection statistics
        """
        try:
            count = self.collection.count()
            
            return {
                'total_documents': count,
                'collection_name': self.collection_name,
                'embedding_dimension': self.collection.metadata.get('embedding_dimension', 'unknown')
            }
            
        except Exception as e:
            logger.error(f"Error getting collection stats: {str(e)}")
            raise Exception(f"Failed to get collection stats: {str(e)}")
    
    async def clear_collection(self) -> bool:
        """
        Clear all documents from the collection.
        
        Returns:
            True if successful
        """
        try:
            self.collection.delete(where={})
            logger.info("Cleared all documents from collection")
            return True
            
        except Exception as e:
            logger.error(f"Error clearing collection: {str(e)}")
            raise Exception(f"Failed to clear collection: {str(e)}")

