#!/usr/bin/env python3
"""
Test script for the memory service

This script tests basic functionality of the memory service including:
- Connection to Cohere and Pinecone
- Storing memories
- Retrieving memories
- Conversation context
"""

import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def test_memory_service():
    """Test the memory service functionality"""
    from memory_service import initialize_memory_service
    from datetime import datetime
    
    print("🧪 Testing Memory Service...")
    
    try:
        # Initialize service
        print("1. Initializing memory service...")
        memory_service = await initialize_memory_service()
        
        if not memory_service:
            print("❌ Failed to initialize memory service - check API keys")
            return
            
        print("✅ Memory service initialized successfully")
        
        # Test 1: Store a memory
        print("\n2. Testing memory storage...")
        from memory_service import MemoryItem
        
        test_memory = MemoryItem(
            content="Il chatbot supporta la creazione di mappe concettuali interattive",
            metadata={"topic": "features", "importance": "high"},
            timestamp=datetime.now(),
            conversation_id="test-conv-123",
            message_type="chat"
        )
        
        success = await memory_service.store_memory(test_memory)
        if success:
            print("✅ Memory stored successfully")
        else:
            print("❌ Failed to store memory")
            return
            
        # Test 2: Retrieve memories
        print("\n3. Testing memory retrieval...")
        memories = await memory_service.retrieve_memories(
            query="mappe concettuali",
            conversation_id="test-conv-123",
            limit=5
        )
        
        print(f"✅ Retrieved {len(memories)} memories")
        for i, memory in enumerate(memories, 1):
            print(f"   {i}. Score: {memory['score']:.3f} - {memory['content'][:50]}...")
        
        # Test 3: Store conversation turn
        print("\n4. Testing conversation storage...")
        success = await memory_service.store_conversation_turn(
            user_message="Come posso creare una nuova mappa concettuale?",
            ai_response="Puoi creare una nuova mappa concettuale cliccando sul pulsante '+ Nuova mappa concettuale' nella sidebar sinistra.",
            conversation_id="test-conv-123",
            additional_metadata={"session": "test"}
        )
        
        if success:
            print("✅ Conversation turn stored successfully")
        else:
            print("❌ Failed to store conversation turn")
            
        # Test 4: Get conversation context
        print("\n5. Testing conversation context...")
        context = await memory_service.get_conversation_context(
            current_message="Dove trovo il pulsante per creare mappe?",
            conversation_id="test-conv-123",
            context_limit=3
        )
        
        if context:
            print("✅ Retrieved conversation context:")
            print(f"   Context length: {len(context)} characters")
            print(f"   Preview: {context[:100]}...")
        else:
            print("❌ No context retrieved")
            
        print("\n🎉 All tests completed successfully!")
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_memory_service())