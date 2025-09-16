import os
import asyncio
from typing import Optional, Dict, Any, List
from loguru import logger
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.exceptions import UnexpectedResponse
import numpy as np


# Load environment variables
load_dotenv()

class QdrantClientWrapper:
    """Client for interacting with Qdrant Cloud vector database."""

    def __init__(self, url: Optional[str] = None, api_key: Optional[str] = None):
        """Initializes the Qdrant client.

        Args:
            url: The Qdrant Cloud URL. If None, loads from QDRANT_URL environment variable.
            api_key: The Qdrant API key. If None, loads from QDRANT_API_KEY environment variable.
        """
        self.url = url or os.getenv("QDRANT_URL")
        self.api_key = api_key or os.getenv("QDRANT_API_KEY")
        self.collection_name = os.getenv("QDRANT_COLLECTION_NAME", "news_articles")
        
        if not self.url:
            raise ValueError("QDRANT_URL environment variable is not configured.")
        if not self.api_key:
            raise ValueError("QDRANT_API_KEY environment variable is not configured.")
        
        # Initialize Qdrant client
        self.client = QdrantClient(
            url=self.url,
            api_key=self.api_key,
            timeout=30.0
        )
        
        # Initialize Azure OpenAI client for embeddings
        self.openai_client = None
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.openai_endpoint = os.getenv("OPENAI_BASE_URL", "https://vibetrader-llm-rag.cognitiveservices.azure.com/")
        self.openai_deployment = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "embedding-stocks")
        self.openai_api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01")
        
        if self.openai_api_key:
            try:
                from openai import AzureOpenAI
                
                # Log the configuration for debugging
                logger.info(f"Initializing Azure OpenAI with:")
                logger.info(f"  - API Version: {self.openai_api_version}")
                logger.info(f"  - Endpoint: {self.openai_endpoint}")
                logger.info(f"  - Deployment: {self.openai_deployment}")
                
                self.openai_client = AzureOpenAI(
                    api_version=self.openai_api_version,
                    azure_endpoint=self.openai_endpoint,
                    api_key=self.openai_api_key
                )
                logger.info(f"Azure OpenAI client initialized for embeddings using deployment: {self.openai_deployment}")
            except Exception as e:
                logger.error(f"Failed to initialize Azure OpenAI client: {str(e)}")
                import traceback
                logger.error(f"Stack trace: {traceback.format_exc()}")
                self.openai_client = None
        else:
            logger.warning("OPENAI_API_KEY not set. Embedding generation will fail.")
        
        logger.info(f"QdrantClient initialized for URL: {self.url}")
        logger.info(f"Using collection: {self.collection_name}")
        
        # Ensure collection exists (run synchronously to avoid async issues)
        # asyncio.create_task(self._ensure_collection_exists())

    async def _ensure_collection_exists(self):
        """Ensures the collection exists with proper configuration."""
        try:
            # Check if collection exists
            collections = self.client.get_collections()
            collection_names = [col.name for col in collections.collections]
            
            if self.collection_name not in collection_names:
                logger.info(f"Creating collection: {self.collection_name}")
                
                # Create collection with proper configuration
                try:
                    self.client.create_collection(
                        collection_name=self.collection_name,
                        vectors_config=models.VectorParams(
                            size=3072,  # text-embedding-3-large embedding size
                            distance=models.Distance.COSINE
                        )
                    )
                    logger.info(f"Successfully created collection {self.collection_name}")
                except Exception as e:
                    logger.error(f"Error creating collection {self.collection_name}: {str(e)}")
                    # Continue execution as the collection might have been created by another process
                
                # Create payload indices - wrapped in try/except to handle individual failures
                try:
                    self.client.create_payload_index(
                        collection_name=self.collection_name,
                        field_name="publishDatePst",
                        field_schema=models.PayloadFieldSchema.DATETIME
                    )
                    logger.info(f"Created publishDatePst index for {self.collection_name}")
                except Exception as e:
                    logger.warning(f"Error creating publishDatePst index: {str(e)}")
                
                try:
                    self.client.create_payload_index(
                        collection_name=self.collection_name,
                        field_name="source",
                        field_schema=models.PayloadFieldSchema.KEYWORD
                    )
                    logger.info(f"Created source index for {self.collection_name}")
                except Exception as e:
                    logger.warning(f"Error creating source index: {str(e)}")
                
                logger.info(f"Collection {self.collection_name} setup complete")
            else:
                logger.info(f"Collection {self.collection_name} already exists")
                
        except Exception as e:
            logger.error(f"Error ensuring collection exists: {str(e)}")
            # Don't re-raise the exception, as we want to continue execution

    async def close(self):
        """Closes the Qdrant client."""
        if self.client:
            self.client.close()
            logger.info("QdrantClient closed.")

    async def check_health(self) -> bool:
        """Checks the health of the Qdrant service."""
        try:
            # Get collections to test connection
            collections = self.client.get_collections()
            logger.info(f"Qdrant health check successful. Found {len(collections.collections)} collections.")
            return True
        except Exception as e:
            logger.error(f"Qdrant health check failed: {e}")
            return False

    async def add_document(self, text_content: str, metadata: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """Adds a document to the Qdrant collection with retry mechanism.
        
        Args:
            text_content: The text content to embed and store.
            metadata: Optional metadata to store with the document.
            
        Returns:
            Dictionary with status and document ID, or None on failure.
        """
        # Retry configuration for cloud environments
        max_retries = 3
        retry_delay_base = 2  # seconds
        
        for attempt in range(max_retries):
            retry_delay = retry_delay_base ** attempt if attempt > 0 else 0
            if attempt > 0:
                logger.info(f"Retry attempt {attempt}/{max_retries} for Qdrant operation after {retry_delay}s delay")
                await asyncio.sleep(retry_delay)
            
            try:
                # Ensure the collection exists
                try:
                    await self._ensure_collection_exists()
                except Exception as e:
                    logger.error(f"Error ensuring collection exists (attempt {attempt+1}): {str(e)}")
                    # Continue anyway, as collection might already exist
                    
                # Generate embedding using Azure OpenAI
                if not self.openai_client:
                    logger.error("Azure OpenAI client not initialized. Cannot generate embeddings.")
                    if attempt < max_retries - 1:
                        continue  # Try again (maybe client will be initialized)
                    return None
                
                # Generate embedding with retry
                embedding = None
                for embed_attempt in range(2):  # Inner retry just for embedding
                    try:    
                        response = self.openai_client.embeddings.create(
                            model=self.openai_deployment,
                            input=text_content
                        )
                        embedding = response.data[0].embedding
                        logger.info(f"Successfully generated embedding with {len(embedding)} dimensions")
                        break  # Success, exit the inner retry loop
                    except Exception as e:
                        logger.error(f"Error generating embedding (attempt {embed_attempt+1}): {str(e)}")
                        if embed_attempt < 1:  # If not the last attempt
                            await asyncio.sleep(1)  # Short delay before retry
                
                if not embedding:
                    logger.error("Failed to generate embedding after retries")
                    if attempt < max_retries - 1:
                        continue  # Try the outer loop again
                    return None
                    
                # Prepare payload
                payload = {
                    "text": text_content[:1000],  # Limit text size in payload
                    "text_length": len(text_content)
                }
                
                # Add metadata to payload
                if metadata:
                    payload.update(metadata)
                
                # Generate unique ID (you might want to use a hash of content + metadata)
                import hashlib
                content_hash = hashlib.md5(f"{text_content[:1000]}{str(metadata)}".encode()).hexdigest()
                
                # Upsert point (insert or update) with increased timeout
                try:
                    operation_timeout = 30 * (attempt + 1)  # Increase timeout with each retry
                    logger.info(f"Upserting to Qdrant with {operation_timeout}s timeout")
                    
                    self.client.upsert(
                        collection_name=self.collection_name,
                        points=[
                            models.PointStruct(
                                id=content_hash,
                                vector=embedding,  # embedding is already a list
                                payload=payload
                            )
                        ],
                        timeout=operation_timeout
                    )
                    
                    logger.info(f"Successfully added document with ID: {content_hash}")
                    return {
                        "status": "success",
                        "document_id": content_hash,
                        "message": "Document added successfully"
                    }
                except Exception as e:
                    logger.error(f"Error upserting point to Qdrant (attempt {attempt+1}): {str(e)}")
                    if attempt < max_retries - 1:
                        continue  # Try again in the outer loop
                    return None
                
            except Exception as e:
                logger.error(f"Error adding document to Qdrant (attempt {attempt+1}): {str(e)}")
                if attempt < max_retries - 1:
                    continue  # Try again
        
        # If we get here, all retries failed
        logger.error("All retry attempts failed for adding document to Qdrant")
        return None

    async def search_documents(self, query: str, limit: int = 10, score_threshold: float = 0.3) -> Optional[List[Dict[str, Any]]]:
        """Searches for documents similar to the query.
        
        Args:
            query: The search query text.
            limit: Maximum number of results to return.
            score_threshold: Minimum similarity score threshold (default: 0.3).
            
        Returns:
            List of matching documents with scores, or None on failure.
        """
        try:
            # Generate query embedding using Azure OpenAI
            if not self.openai_client:
                logger.error("Azure OpenAI client not initialized. Cannot generate embeddings.")
                return None
                
            response = self.openai_client.embeddings.create(
                model=self.openai_deployment,
                input=query
            )
            query_embedding = response.data[0].embedding
            
            # Search in collection
            search_results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,  # query_embedding is already a list
                limit=limit,
                score_threshold=score_threshold
            )
            
            # Format results
            results = []
            for result in search_results:
                results.append({
                    "id": result.id,
                    "score": result.score,
                    "payload": result.payload
                })
            
            logger.info(f"Search returned {len(results)} results for query: {query[:50]}...")
            return results
            
        except Exception as e:
            logger.error(f"Error searching documents in Qdrant: {e}")
            return None

    async def delete_document(self, document_id: str) -> bool:
        """Deletes a document from the collection.
        
        Args:
            document_id: The ID of the document to delete.
            
        Returns:
            True if successful, False otherwise.
        """
        try:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=models.PointIdsList(
                    points=[document_id]
                )
            )
            logger.info(f"Successfully deleted document with ID: {document_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting document {document_id}: {e}")
            return False

    async def delete_documents_older_than(self, hours: int) -> Optional[Dict[str, Any]]:
        """Deletes documents older than specified hours.
        
        Args:
            hours: Age threshold in hours.
            
        Returns:
            Dictionary with status and deleted count, or None on failure.
        """
        try:
            from datetime import datetime, timedelta
            import pytz
            
            # Calculate cutoff time in PST
            pst = pytz.timezone('US/Pacific')
            cutoff_time = datetime.now(pst) - timedelta(hours=hours)
            
            # Search for old documents
            old_docs = self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="publishDatePst",
                            range=models.DatetimeRange(
                                lt=cutoff_time.isoformat()
                            )
                        )
                    ]
                ),
                limit=1000  # Adjust based on your needs
            )
            
            if not old_docs[0]:  # No documents to delete
                return {
                    "status": "no_action",
                    "deleted_count": 0,
                    "message": "No documents older than specified hours found"
                }
            
            # Delete old documents
            doc_ids = [doc.id for doc in old_docs[0]]
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=models.PointIdsList(points=doc_ids)
            )
            
            logger.info(f"Deleted {len(doc_ids)} documents older than {hours} hours")
            return {
                "status": "success",
                "deleted_count": len(doc_ids),
                "message": f"Deleted {len(doc_ids)} documents older than {hours} hours"
            }
            
        except Exception as e:
            logger.error(f"Error deleting old documents: {e}")
            return None

    async def clear_all_documents(self) -> Optional[Dict[str, Any]]:
        """Clears all documents from the collection.
        
        Returns:
            Dictionary with status and message, or None on failure.
        """
        try:
            # Get collection info to count documents
            collection_info = self.client.get_collection(self.collection_name)
            doc_count = collection_info.points_count
            
            # Delete all points
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=models.FilterSelector(
                    filter=models.Filter()
                )
            )
            
            logger.info(f"Cleared all {doc_count} documents from collection")
            return {
                "status": "success",
                "message": f"Cleared all {doc_count} documents from collection"
            }
            
        except Exception as e:
            logger.error(f"Error clearing all documents: {e}")
            return None

    async def get_collection_stats(self) -> Optional[Dict[str, Any]]:
        """Gets statistics about the collection.
        
        Returns:
            Dictionary with collection statistics, or None on failure.
        """
        try:
            collection_info = self.client.get_collection(self.collection_name)
            return {
                "collection_name": self.collection_name,
                "points_count": collection_info.points_count,
                "segments_count": collection_info.segments_count,
                "status": collection_info.status
            }
        except Exception as e:
            logger.error(f"Error getting collection stats: {e}")
            return None

# Example usage for testing
async def _test_client():
    """Test function for the Qdrant client."""
    client = None
    try:
        client = QdrantClientWrapper()
        
        # Test health check
        health_ok = await client.check_health()
        print(f"Health check: {'OK' if health_ok else 'FAILED'}")
        
        # Test adding document
        test_text = "This is a test document for Qdrant integration."
        test_metadata = {
            "source": "test",
            "publishDatePst": "2024-01-01T00:00:00-08:00",
            "title": "Test Article"
        }
        
        add_result = await client.add_document(test_text, test_metadata)
        print(f"Add document result: {add_result}")
        
        # Test search
        search_results = await client.search_documents("test document")
        print(f"Search results: {search_results}")
        
        # Test stats
        stats = await client.get_collection_stats()
        print(f"Collection stats: {stats}")
        
    except Exception as e:
        print(f"Test failed: {e}")
    finally:
        if client:
            await client.close()

if __name__ == "__main__":
    asyncio.run(_test_client())
