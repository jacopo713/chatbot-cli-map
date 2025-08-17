#!/usr/bin/env python3
"""
Test script per verificare le migliorie al memory service
"""
import asyncio
import os
import sys
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add backend to path
sys.path.append(os.path.dirname(__file__))

from memory_service import MemoryService, MemoryConfig, MemoryItem

async def test_memory_improvements():
    """Test delle migliorie implementate"""
    
    # Initialize memory service
    config = MemoryConfig(
        cohere_api_key=os.getenv("COHERE_API_KEY", ""),
        pinecone_api_key=os.getenv("PINECONE_API_KEY", ""),
        pinecone_index_name=os.getenv("PINECONE_INDEX", "chatbot-cli-map"),
        pinecone_host=os.getenv("PINECONE_HOST", "https://chatbot-cli-map-mp69iv8.svc.aped-4627-b74a.pinecone.io")
    )
    
    if not config.cohere_api_key or not config.pinecone_api_key:
        print("❌ API keys not configured")
        return
    
    memory_service = MemoryService(config)
    await memory_service.initialize()
    
    print("🧪 Testing Memory Service Improvements")
    print("=" * 50)
    
    # Test 1: Store personal information
    print("\n1️⃣ Testing personal information storage...")
    personal_info = "Mi chiamo Marco e lavoro come sviluppatore software"
    
    personal_memory = MemoryItem(
        content=personal_info,
        metadata={"role": "user", "importance": 0.9},
        timestamp=datetime.now(),
        conversation_id="global",
        message_type="personal"
    )
    
    success = await memory_service.store_memory(personal_memory)
    print(f"✅ Personal info stored: {success}")
    
    # Test 2: Store conversation turn
    print("\n2️⃣ Testing conversation turn storage...")
    user_msg = "Voglio imparare a cucinare la torta di mele con cannella"
    ai_response = "Ecco una ricetta semplice per la torta di mele con cannella..."
    
    success = await memory_service.store_conversation_turn(
        user_message=user_msg,
        ai_response=ai_response,
        conversation_id="test-conv-123",
        additional_metadata={"session": "test"}
    )
    print(f"✅ Conversation turn stored: {success}")
    
    # Test 3: Query with new system
    print("\n3️⃣ Testing improved retrieval...")
    query = "torta di mele con cannella"
    
    memories = await memory_service.retrieve_memories(
        query=query,
        conversation_id="test-conv-123",
        limit=5
    )
    
    print(f"🔍 Query: '{query}'")
    print(f"📊 Found {len(memories)} memories")
    
    for i, memory in enumerate(memories, 1):
        score = memory.get('score', 0)
        text = memory.get('text', memory.get('content', ''))[:80]
        msg_type = memory.get('message_type', 'unknown')
        role = memory.get('role', 'unknown')
        
        print(f"  {i}. Score: {score:.3f} | Type: {msg_type} | Role: {role}")
        print(f"     Text: {text}...")
    
    # Test 4: Context retrieval
    print("\n4️⃣ Testing context retrieval...")
    context = await memory_service.get_conversation_context(
        current_message="Come posso migliorare la ricetta?",
        conversation_id="test-conv-123",
        context_limit=3
    )
    
    if context:
        print("📝 Context retrieved:")
        print(context)
    else:
        print("❌ No context found")
    
    # Test 5: Embedding functions
    print("\n5️⃣ Testing embedding functions...")
    test_text = "torta di mele"
    
    doc_embedding = await memory_service._embed_doc(test_text)
    query_embedding = await memory_service._embed_query(test_text)
    
    print(f"📐 Document embedding length: {len(doc_embedding)}")
    print(f"📐 Query embedding length: {len(query_embedding)}")
    
    # Calculate similarity between doc and query embeddings of same text
    def cosine_similarity(a, b):
        dot_product = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5
        return dot_product / (norm_a * norm_b)
    
    similarity = cosine_similarity(doc_embedding, query_embedding)
    print(f"🎯 Self-similarity (doc vs query): {similarity:.3f}")
    
    if similarity > 0.6:
        print("✅ Good self-similarity!")
    else:
        print("⚠️ Low self-similarity - may need investigation")
    
    print("\n" + "=" * 50)
    print("🎉 Test completed!")

if __name__ == "__main__":
    asyncio.run(test_memory_improvements())