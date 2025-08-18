#!/usr/bin/env python3
"""
Test del sistema semplificato con singola chiamata IA
"""
import sys
sys.path.append('.')

import asyncio
from hybrid_memory_service import HybridMemoryService, HybridMemoryConfig

async def test_single_ai_call():
    """Test veloce dell'estrazione con singola chiamata IA"""
    
    config = HybridMemoryConfig(
        cohere_api_key="dummy",
        pinecone_api_key="dummy"
    )
    service = HybridMemoryService(config)
    
    print("🚀 Test estrazione IA - SINGOLA CHIAMATA\n")
    
    # Test con il messaggio completo
    test_message = "mi chiamo jacopo, ho 29 anni, vivo a brovello carpugnino, mi piacciono i cani e i gatti, sono ansioso e ho il doc"
    
    print(f"📝 Test messaggio: \"{test_message}\"\n")
    
    try:
        print("⏳ Esecuzione estrazione IA...")
        facts = await service._extract_canonical_facts(test_message)
        
        print(f"\n✅ Estrazione completata!")
        print(f"📊 Fatti estratti: {len(facts)}\n")
        
        if facts:
            print("📋 RISULTATI:")
            for i, fact in enumerate(facts, 1):
                fact_type = fact.split(':')[0] if ':' in fact else 'unknown'
                fact_value = fact.split(':', 1)[1] if ':' in fact else fact
                
                # Emoji per tipo
                emoji = {
                    'user_name': '👤',
                    'user_location': '📍', 
                    'user_likes': '❤️',
                    'user_condition': '🏥',
                    'user_age': '🎂',
                    'user_job': '💼',
                    'user_skill': '🔧',
                    'user_goal': '🎯',
                    'user_experience': '📚',
                    'user_relationship': '👥',
                    'user_preference': '⭐'
                }.get(fact_type, '📋')
                
                print(f"  {i}. {emoji} {fact_type}: {fact_value}")
        else:
            print("❌ Nessun fatto estratto")
            
    except Exception as e:
        print(f"❌ Errore: {e}")
    
    print("\n" + "="*50)
    print("✅ Test completato!")

if __name__ == "__main__":
    asyncio.run(test_single_ai_call())