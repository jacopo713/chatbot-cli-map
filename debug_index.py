#!/usr/bin/env python3
"""
Debug script per verificare cosa c'è nell'indice Pinecone
"""
import asyncio
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add backend to path
sys.path.append(os.path.dirname(__file__))

from memory_service import MemoryService, MemoryConfig
from pinecone import Pinecone

async def debug_index():
    """Debug dell'indice Pinecone"""
    
    # Initialize Pinecone directly
    pinecone_client = Pinecone(api_key=os.getenv("PINECONE_API_KEY", ""))
    index = pinecone_client.Index(
        name=os.getenv("PINECONE_INDEX", "chatbot-cli-map"),
        host=os.getenv("PINECONE_HOST", "https://chatbot-cli-map-mp69iv8.svc.aped-4627-b74a.pinecone.io")
    )
    
    print("🔍 Debugging Pinecone Index")
    print("=" * 50)
    
    # Get index stats
    stats = await asyncio.to_thread(index.describe_index_stats)
    print(f"📊 Total vectors: {stats.get('total_vector_count', 0)}")
    print(f"📊 Namespaces: {stats.get('namespaces', {})}")
    
    # Try to fetch some recent records by doing a dummy query
    dummy_vector = [0.1] * 1024  # Dummy vector
    
    print("\n🔍 Querying with no filters (top 10)...")
    try:
        response = await asyncio.to_thread(
            index.query,
            vector=dummy_vector,
            top_k=10,
            include_metadata=True
        )
        
        print(f"Found {len(response.matches)} matches")
        for i, match in enumerate(response.matches, 1):
            metadata = match.metadata or {}
            print(f"  {i}. ID: {match.id[:20]}...")
            print(f"     Score: {match.score:.3f}")
            print(f"     Metadata keys: {list(metadata.keys())}")
            
            # Show relevant metadata
            for key in ['message_type', 'scope', 'role', 'text', 'content']:
                if key in metadata:
                    value = str(metadata[key])[:60]
                    print(f"     {key}: {value}")
            print()
    
    except Exception as e:
        print(f"❌ Query failed: {e}")
    
    # Test specific filters
    print("\n🔍 Testing filter for personal messages...")
    try:
        response = await asyncio.to_thread(
            index.query,
            vector=dummy_vector,
            top_k=5,
            include_metadata=True,
            filter={"message_type": "personal"}
        )
        print(f"Personal messages: {len(response.matches)}")
    except Exception as e:
        print(f"❌ Personal filter failed: {e}")
    
    print("\n🔍 Testing filter for chat messages...")
    try:
        response = await asyncio.to_thread(
            index.query,
            vector=dummy_vector,
            top_k=5,
            include_metadata=True,
            filter={"message_type": "chat"}
        )
        print(f"Chat messages: {len(response.matches)}")
    except Exception as e:
        print(f"❌ Chat filter failed: {e}")

if __name__ == "__main__":
    asyncio.run(debug_index())