#!/usr/bin/env python3
"""
Qdrant Collection Data Cleanup Script
------------------------------------
This script clears all documents from a Qdrant collection
while preserving the collection structure and configuration.

Usage:
  python clear_qdrant_data.py
"""

import os
import sys
from datetime import datetime
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.http import models

# Load environment variables
load_dotenv()

# Get Qdrant configuration from environment variables
QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
QDRANT_COLLECTION_NAME = os.getenv("QDRANT_COLLECTION_NAME", "news_articles")

def print_status(message):
    """Print a status message with timestamp."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")

def clear_collection_data():
    """Clear all documents from the Qdrant collection while preserving the collection itself."""
    print_status(f"Clearing all documents from collection '{QDRANT_COLLECTION_NAME}'...")
    
    # Check if credentials are available
    if not QDRANT_URL or not QDRANT_API_KEY:
        print_status("❌ ERROR: Missing Qdrant credentials. Check your .env file.")
        return False
    
    try:
        # Initialize the Qdrant client
        print_status(f"Connecting to Qdrant at {QDRANT_URL}...")
        client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
        
        # Check if collection exists
        collections = client.get_collections()
        collection_names = [col.name for col in collections.collections]
        
        if QDRANT_COLLECTION_NAME not in collection_names:
            print_status(f"❌ Collection '{QDRANT_COLLECTION_NAME}' does not exist.")
            return False
        
        # Get current count of documents
        collection_info = client.get_collection(QDRANT_COLLECTION_NAME)
        doc_count = collection_info.points_count
        print_status(f"Found {doc_count} documents in collection '{QDRANT_COLLECTION_NAME}'")
        
        if doc_count == 0:
            print_status("✅ Collection is already empty. Nothing to clear.")
            return True
        
        # Delete all points using Filter() with no conditions (matches everything)
        print_status(f"Deleting all {doc_count} documents...")
        client.delete(
            collection_name=QDRANT_COLLECTION_NAME,
            points_selector=models.FilterSelector(
                filter=models.Filter()
            )
        )
        
        # Verify deletion
        collection_info = client.get_collection(QDRANT_COLLECTION_NAME)
        new_doc_count = collection_info.points_count
        
        if new_doc_count == 0:
            print_status(f"✅ Successfully cleared all {doc_count} documents from collection.")
            return True
        else:
            print_status(f"⚠️ Partial deletion: {new_doc_count} documents remain out of {doc_count}.")
            return False
        
    except Exception as e:
        print_status(f"❌ Error clearing collection data: {str(e)}")
        return False

if __name__ == "__main__":
    print_status("=== Qdrant Collection Data Cleanup Tool ===")
    print_status(f"Qdrant URL: {QDRANT_URL}")
    print_status(f"Collection: {QDRANT_COLLECTION_NAME}")
    
    success = clear_collection_data()
    
    if success:
        print_status("✅ All documents successfully removed from collection")
        sys.exit(0)
    else:
        print_status("❌ Failed to completely clear collection data")
        sys.exit(1)