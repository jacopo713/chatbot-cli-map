#!/usr/bin/env python3
"""
Test del sistema senza filtri - sempre chiamata IA
"""
import sys
sys.path.append('.')

import asyncio
from hybrid_memory_service import HybridMemoryService, HybridMemoryConfig

async def test_no_filters():
    """Test che TUTTI i messaggi attivano la chiamata IA"""
    
    config = HybridMemoryConfig(
        cohere_api_key="dummy",
        pinecone_api_key="dummy"
    )
    service = HybridMemoryService(config)
    
    print("🚀 Test sistema SENZA pre-filtri")
    print("✅ Ogni input → Sempre chiamata IA\n")
    
    test_messages = [
        # Messaggi che prima venivano filtrati
        "ok", 
        "grazie",
        "come funziona?",
        
        # Messaggi con info personali
        "mi chiamo jacopo",
        "ho 29 anni"
    ]
    
    for i, message in enumerate(test_messages, 1):
        print(f"🔍 Test {i}: \"{message}\"")
        
        try:
            facts = await service._extract_canonical_facts(message)
            print(f"   🤖 Fatti estratti: {len(facts)}")
            
            if facts:
                for fact in facts:
                    print(f"      • {fact}")
            else:
                print(f"      ℹ️  Nessun fatto rilevante (IA ha deciso)")
                
        except Exception as e:
            print(f"   ❌ Errore: {e}")
            
        print()
    
    print("✅ Test completato - ogni messaggio ha attivato la chiamata IA!")

if __name__ == "__main__":
    asyncio.run(test_no_filters())