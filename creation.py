from qdrant_client import QdrantClient
from qdrant_client.http import models
from loguru import logger
import os
from dotenv import load_dotenv
import asyncio

# Load environment variables
load_dotenv()

async def create_collection():
    """Create the news_articles collection in Qdrant."""
    try:
        # Initialize Qdrant client
        client = QdrantClient(
            url=os.getenv("QDRANT_URL"),
            api_key=os.getenv("QDRANT_API_KEY"),
            timeout=60.0
        )
        
        logger.info("Creating news_articles collection...")
        
        # Create the collection
        client.create_collection(
            collection_name="news_articles",
            vectors_config=models.VectorParams(
                size=3072,  # OpenAI embedding dimension
                distance=models.Distance.COSINE
            ),
            on_disk_payload=True,  # Store payload on disk to save RAM
        )
        
        # Create payload indexes
        logger.info("Creating payload indexes...")
        
        client.create_payload_index(
            collection_name="news_articles",
            field_name="publishDatePst",
            field_schema=models.PayloadSchemaType.DATETIME
        )
        
        client.create_payload_index(
            collection_name="news_articles",
            field_name="source",
            field_schema=models.PayloadSchemaType.KEYWORD
        )
        
        # Verify collection exists
        collections = client.get_collections()
        if any(collection.name == "news_articles" for collection in collections.collections):
            logger.info("✅ Collection news_articles created successfully!")
        else:
            logger.error("❌ Failed to create collection!")
            
    except Exception as e:
        logger.error(f"Error creating collection: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(create_collection())