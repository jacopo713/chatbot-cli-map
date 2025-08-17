#!/usr/bin/env python3
"""
Test per diagnosticare lo stato attuale delle memorie
"""
import asyncio
import sys
sys.path.append('.')

from hybrid_memory_service import get_hybrid_memory_service

async def debug_current_memories():
    """Debug dello stato attuale delle memorie"""
    
    print("🔍 Diagnostica stato memorie\n")
    
    # Prova a recuperare le memorie per diverse query
    service = get_hybrid_memory_service()
    if not service:
        print("❌ Hybrid memory service non disponibile")
        return
        
    # Test queries
    queries = [
        "dimmi tutto su di me",
        "jacopo", 
        "nome",
        "informazioni personali",
        "chi sono"
    ]
    
    print(f"Service config:")
    print(f"  • similarity_threshold: {service.config.similarity_threshold}")
    print(f"  • default limit: 20")
    print(f"  • context_limit: 15")
    print()
    
    for query in queries:
        try:
            print(f"🔎 Query: '{query}'")
            
            memories = await service.retrieve_memories(
                query=query,
                conversation_id=None,  # Global search
                limit=20,
                include_recent=True
            )
            
            print(f"   → Trovate {len(memories)} memorie")
            
            for i, mem in enumerate(memories[:5]):  # Show first 5
                content = mem.get('content', '')[:50] + '...' if len(mem.get('content', '')) > 50 else mem.get('content', '')
                score = mem.get('score', 0)
                msg_type = mem.get('message_type', 'unknown')
                print(f"     {i+1}. [{msg_type}] {content} (score: {score:.3f})")
            
            if len(memories) > 5:
                print(f"     ... e altre {len(memories)-5} memorie")
            print()
            
        except Exception as e:
            print(f"   ❌ Errore: {e}")
            print()

if __name__ == "__main__":
    asyncio.run(debug_current_memories())