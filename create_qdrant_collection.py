#!/usr/bin/env python3
"""
Quick script to create the Qdrant collection for NewsRagnarok Crawler
Run this in Kudu console to fix the collection issue
"""

import os
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams
from openai import AzureOpenAI
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_qdrant_collection():
    """Create the news_article collection in Qdrant"""
    
    try:
        # Get environment variables
        qdrant_url = os.environ.get('QDRANT_URL')
        qdrant_api_key = os.environ.get('QDRANT_API_KEY')
        azure_endpoint = os.environ.get('AZURE_OPENAI_ENDPOINT')
        api_key = os.environ.get('AZURE_OPENAI_API_KEY')
        deployment = os.environ.get('AZURE_OPENAI_EMBEDDING_MODEL', 'text-embedding-3-large')
        
        print(f"🔍 Checking environment variables...")
        print(f"   QDRANT_URL: {'✅ Set' if qdrant_url else '❌ Missing'}")
        print(f"   QDRANT_API_KEY: {'✅ Set' if qdrant_api_key else '❌ Missing'}")
        print(f"   AZURE_OPENAI_ENDPOINT: {'✅ Set' if azure_endpoint else '❌ Missing'}")
        print(f"   AZURE_OPENAI_API_KEY: {'✅ Set' if api_key else '❌ Missing'}")
        
        if not qdrant_url:
            print("❌ QDRANT_URL is required!")
            return False
        
        # Initialize Qdrant client
        print(f"🔗 Connecting to Qdrant at {qdrant_url}...")
        client = QdrantClient(url=qdrant_url, api_key=qdrant_api_key)
        
        collection_name = 'news_article'
        
        # Check if collection exists
        print(f"🔍 Checking if collection '{collection_name}' exists...")
        collections = client.get_collections()
        collection_names = [col.name for col in collections.collections]
        
        if collection_name in collection_names:
            print(f"✅ Collection '{collection_name}' already exists!")
            return True
        
        print(f"📦 Collection '{collection_name}' doesn't exist, creating...")
        
        # Determine vector size
        if azure_endpoint and api_key:
            try:
                print(f"🧠 Testing Azure OpenAI embedding to determine vector size...")
                openai_client = AzureOpenAI(
                    azure_endpoint=azure_endpoint,
                    api_key=api_key,
                    api_version='2024-02-01'
                )
                
                # Test embedding to get vector size
                response = openai_client.embeddings.create(
                    input=['test'],
                    model=deployment
                )
                vector_size = len(response.data[0].embedding)
                print(f"✅ Determined vector size: {vector_size}")
                
            except Exception as e:
                print(f"⚠️ Could not determine vector size from Azure OpenAI: {e}")
                print(f"📏 Using default vector size: 3072")
                vector_size = 3072
        else:
            print(f"📏 Using default vector size: 3072")
            vector_size = 3072
        
        # Create collection
        print(f"🏗️ Creating collection '{collection_name}' with vector size {vector_size}...")
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(
                size=vector_size,
                distance=Distance.COSINE
            )
        )
        
        print(f"✅ Collection '{collection_name}' created successfully!")
        
        # Verify creation
        collections = client.get_collections()
        collection_names = [col.name for col in collections.collections]
        if collection_name in collection_names:
            print(f"✅ Verification: Collection '{collection_name}' is now available")
            return True
        else:
            print(f"❌ Verification failed: Collection '{collection_name}' not found")
            return False
            
    except Exception as e:
        print(f"❌ Error creating Qdrant collection: {e}")
        return False

if __name__ == "__main__":
    print("🚀 NewsRagnarok Qdrant Collection Creator")
    print("=" * 50)
    
    success = create_qdrant_collection()
    
    if success:
        print("\n🎉 SUCCESS: Qdrant collection is ready!")
        print("📝 You can now restart your crawler and it should work properly.")
    else:
        print("\n❌ FAILED: Could not create Qdrant collection.")
        print("📝 Check your environment variables and try again.")
