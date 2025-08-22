import os
from typing import Optional, Dict, Any, List
from loguru import logger
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class VectorClient:
    """Unified client for vector database operations using Qdrant."""
    
    def __init__(self):
        """Initialize the Qdrant vector client."""
        from .qdrant_client import QdrantClientWrapper
        self.client = QdrantClientWrapper()
        self.backend = "qdrant"  # Keep for compatibility
        logger.info("Initialized Qdrant vector client")

    async def close(self):
        """Close the vector client."""
        if self.client:
            await self.client.close()

    async def check_health(self) -> bool:
        """Check the health of the vector service."""
        try:
            return await self.client.check_health()
        except Exception as e:
            logger.error(f"Health check failed for Qdrant: {e}")
            return False

    async def add_document(self, text_content: str, metadata: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """Add a document to the vector database."""
        try:
            return await self.client.add_document(text_content, metadata)
        except Exception as e:
            logger.error(f"Error adding document to Qdrant: {e}")
            return None

    async def search_documents(self, query: str, limit: int = 10, score_threshold: float = 0.7) -> Optional[List[Dict[str, Any]]]:
        """Search for documents similar to the query."""
        try:
            return await self.client.search_documents(query, limit, score_threshold)
        except Exception as e:
            logger.error(f"Error searching documents in Qdrant: {e}")
            return None

    async def delete_document(self, document_id: str) -> bool:
        """Delete a document from the vector database."""
        try:
            return await self.client.delete_document(document_id)
        except Exception as e:
            logger.error(f"Error deleting document from Qdrant: {e}")
            return False

    async def delete_documents_older_than(self, hours: int) -> Optional[Dict[str, Any]]:
        """Delete documents older than specified hours."""
        try:
            return await self.client.delete_documents_older_than(hours)
        except Exception as e:
            logger.error(f"Error deleting old documents from Qdrant: {e}")
            return None

    async def clear_all_documents(self) -> Optional[Dict[str, Any]]:
        """Clear all documents from the vector database."""
        try:
            return await self.client.clear_all_documents()
        except Exception as e:
            logger.error(f"Error clearing documents from Qdrant: {e}")
            return None

    async def get_collection_stats(self) -> Optional[Dict[str, Any]]:
        """Get collection statistics."""
        try:
            return await self.client.get_collection_stats()
        except Exception as e:
            logger.error(f"Error getting stats from Qdrant: {e}")
            return None

# Factory function for easy client creation
def create_vector_client() -> VectorClient:
    """Factory function to create a Qdrant vector client.
    
    Returns:
        VectorClient instance
    """
    return VectorClient()


