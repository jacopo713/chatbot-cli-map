#!/usr/bin/env python3
"""
Test del nuovo prompt inglese con input multilingua
"""
import sys
sys.path.append('.')

import asyncio
from hybrid_memory_service import HybridMemoryService, HybridMemoryConfig

async def test_multilingual_extraction():
    """Test estrazione con prompt inglese su diversi linguaggi"""
    
    config = HybridMemoryConfig(
        cohere_api_key="dummy",
        pinecone_api_key="dummy"
    )
    service = HybridMemoryService(config)
    
    print("🌍 Test prompt INGLESE con input MULTILINGUA")
    print("="*50)
    
    test_cases = [
        # Italiano
        ("🇮🇹 Italiano", "mi chiamo jacopo, ho 29 anni, vivo a brovello carpugnino"),
        
        # Inglese  
        ("🇺🇸 English", "my name is john, I'm 25 years old, I live in New York"),
        
        # Francese
        ("🇫🇷 Français", "je m'appelle marie, j'ai 30 ans, j'habite à paris"),
        
        # Spagnolo
        ("🇪🇸 Español", "me llamo carlos, tengo 35 años, vivo en madrid"),
        
        # Non-personal (dovrebbe restituire NO_INFORMATION)
        ("❓ Generic", "what's the weather today?"),
        ("❓ Generico", "che tempo fa oggi?")
    ]
    
    for language, message in test_cases:
        print(f"\n🔍 {language}")
        print(f"   Input: \"{message}\"")
        
        try:
            facts = await service._extract_canonical_facts(message)
            
            if facts:
                print(f"   ✅ Extracted {len(facts)} facts:")
                for fact in facts:
                    fact_type = fact.split(':')[0] if ':' in fact else 'unknown'
                    fact_value = fact.split(':', 1)[1] if ':' in fact else fact
                    
                    emoji = {
                        'user_name': '👤',
                        'user_age': '🎂',
                        'user_location': '📍',
                        'user_likes': '❤️',
                        'user_condition': '🏥',
                        'user_job': '💼'
                    }.get(fact_type, '📋')
                    
                    print(f"      {emoji} {fact_type}: {fact_value}")
            else:
                print(f"   ⚪ No information extracted (AI decided not relevant)")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    print(f"\n" + "="*50)
    print("✅ Test multilingua completato!")

if __name__ == "__main__":
    asyncio.run(test_multilingual_extraction())