#!/usr/bin/env python3
"""
Test veloce dopo la correzione dei filtri
"""
import sys
sys.path.append('.')

import asyncio
from hybrid_memory_service import HybridMemoryService, HybridMemoryConfig

async def test_quick_fix():
    """Test veloce con messaggio semplice"""
    
    config = HybridMemoryConfig(
        cohere_api_key="dummy",
        pinecone_api_key="dummy"
    )
    service = HybridMemoryService(config)
    
    # Test con messaggio molto semplice
    test_message = "mi chiamo jacopo"
    
    print(f"🔍 Test: '{test_message}'")
    
    try:
        # Test solo l'estrazione (senza la chiamata IA complessa)
        print("⏳ Controllo filtri...")
        
        # Check filtri
        message_lower = test_message.lower().strip()
        
        # Skip very short messages
        if len(test_message.split()) < 2:
            print("❌ FILTRATO: Messaggio troppo corto")
            return
            
        # Skip patterns
        skip_patterns = [
            "come funziona", "help me", "aiuto per", "grazie mille", 
            "perfetto grazie", "ok bene", "ciao ciao", "salve a tutti"
        ]
        
        if any(pattern in message_lower for pattern in skip_patterns):
            print("❌ FILTRATO: Pattern di skip trovato")
            return
            
        # Only skip if it's an exact match
        if message_lower.strip() in ["ok", "bene", "perfetto", "sì", "no", "ciao", "salve", "grazie"]:
            print("❌ FILTRATO: Match esatto con parola da escludere")
            return
            
        print("✅ Filtri superati! Messaggio valido per estrazione.")
        print(f"📏 Parole: {len(test_message.split())}")
        print(f"🔤 Minuscolo: '{message_lower}'")
        
        # Ora prova a estrarre
        print("🤖 Esecuzione estrazione IA...")
        facts = await service._extract_canonical_facts(test_message)
        
        print(f"✅ Estrazione completata: {len(facts)} fatti")
        for fact in facts:
            print(f"   - {fact}")
            
    except Exception as e:
        print(f"❌ Errore: {e}")

if __name__ == "__main__":
    asyncio.run(test_quick_fix())