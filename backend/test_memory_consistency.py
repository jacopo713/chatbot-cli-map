#!/usr/bin/env python3
"""
Script per testare la consistenza del recupero memoria
"""

import asyncio
import aiohttp
import json
import time
from typing import Dict, Any

API_BASE = "http://localhost:8000"

async def test_memory_search():
    """Test direct memory search"""
    async with aiohttp.ClientSession() as session:
        payload = {"query": "Jacopo", "limit": 3}
        async with session.post(f"{API_BASE}/api/memory/search", json=payload) as resp:
            data = await resp.json()
            print(f"📋 Memory Search Results: {data['count']} memories found")
            for i, memory in enumerate(data['memories'][:2]):
                print(f"  {i+1}. {memory['content'][:50]}... (score: {memory['score']:.3f})")
            return data['count'] > 0

async def test_chat_memory(test_id: str):
    """Test chat with memory retrieval"""
    async with aiohttp.ClientSession() as session:
        payload = {
            "message": "ciao",
            "conversation_id": f"consistency_test_{test_id}",
            "history": []
        }
        async with session.post(f"{API_BASE}/api/chat", json=payload) as resp:
            response_text = await resp.text()
            contains_jacopo = "jacopo" in response_text.lower()
            print(f"💬 Chat Test {test_id}: {'✅ Found Jacopo' if contains_jacopo else '❌ No Jacopo'}")
            print(f"    Response: {response_text[:100]}...")
            return contains_jacopo

async def test_consistency():
    """Run consistency tests"""
    print("🧪 Testing Memory Consistency")
    print("=" * 50)
    
    # Test 1: Direct memory search
    search_works = await test_memory_search()
    print()
    
    # Test 2: Multiple chat tests
    chat_results = []
    for i in range(5):
        result = await test_chat_memory(i)
        chat_results.append(result)
        await asyncio.sleep(0.5)  # Small delay between tests
    
    print()
    print("📊 Results Summary:")
    print(f"   Direct search works: {'✅' if search_works else '❌'}")
    print(f"   Chat success rate: {sum(chat_results)}/{len(chat_results)} ({sum(chat_results)/len(chat_results)*100:.0f}%)")
    
    if sum(chat_results) < len(chat_results):
        print("⚠️  Inconsistent behavior detected!")
        return False
    else:
        print("✅ Memory retrieval is consistent!")
        return True

if __name__ == "__main__":
    asyncio.run(test_consistency())