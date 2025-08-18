#!/usr/bin/env python3
"""
Test del nuovo sistema di estrazione basato su IA
"""
import sys
sys.path.append('.')

import asyncio
from hybrid_memory_service import HybridMemoryService, HybridMemoryConfig

async def test_ai_extraction():
    """Test dell'estrazione IA con diversi tipi di messaggio"""
    
    config = HybridMemoryConfig(
        cohere_api_key="dummy",
        pinecone_api_key="dummy"
    )
    service = HybridMemoryService(config)
    
    print("🤖 Test estrazione fatti basata su IA\n")
    
    # Test cases - vari tipi di messaggi
    test_messages = [
        # Informazioni personali complete
        "mi chiamo jacopo, ho 29 anni, vivo a brovello carpugnino, mi piacciono i cani e i gatti, sono ansioso e ho il doc",
        
        # Informazioni parziali
        "studio informatica all'università di milano",
        
        # Solo preferenze
        "mi piace suonare la chitarra e ascoltare jazz",
        
        # Condizioni/stati
        "ho problemi di ansia sociale e faccio terapia",
        
        # Domande generiche (dovrebbero essere filtrate)
        "che tempo fa oggi?",
        "come funziona pinecone?",
        "dimmi tutto quello che sai su di me",
        
        # Conversazione normale (dovrebbe essere filtrata)  
        "grazie per l'aiuto",
        "ok perfetto",
        
        # Informazioni di lavoro
        "lavoro come sviluppatore software in una startup"
    ]
    
    print("📋 Test messaggi:")
    for i, message in enumerate(test_messages, 1):
        print(f"  {i}. \"{message}\"")
    print()
    
    for i, message in enumerate(test_messages, 1):
        print(f"🔍 Test {i}: \"{message[:40]}{'...' if len(message) > 40 else ''}\"")
        
        try:
            # Test valutazione rilevanza
            is_relevant = await service._should_extract_info(message)
            print(f"   📊 Rilevanza: {'✅ RILEVANTE' if is_relevant else '❌ NON_RILEVANTE'}")
            
            if is_relevant:
                # Test estrazione fatti
                facts = await service._extract_canonical_facts(message)
                print(f"   📝 Fatti estratti: {len(facts)}")
                
                for j, fact in enumerate(facts, 1):
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
                    
                    print(f"      {emoji} {fact_type}: {fact_value}")
            else:
                print("   ⏭️  Saltato (non rilevante)")
                
        except Exception as e:
            print(f"   ❌ Errore: {e}")
            
        print()
    
    print("✅ Test completato!")

if __name__ == "__main__":
    asyncio.run(test_ai_extraction())