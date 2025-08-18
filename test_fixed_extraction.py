#!/usr/bin/env python3
"""
Test per verificare l'estrazione corretta dei fatti dopo le correzioni
"""
import sys
sys.path.append('.')

from hybrid_memory_service import HybridMemoryService, HybridMemoryConfig

def test_fixed_extraction():
    """Test dell'estrazione corretta dei fatti"""
    
    config = HybridMemoryConfig(
        cohere_api_key="dummy",
        pinecone_api_key="dummy"
    )
    service = HybridMemoryService(config)
    
    # Test con il messaggio problematico
    test_message = "mi chiamo jacopo, vivo a brovello carpugnino, mi piacciono i cani e i gatti e tutti gli animali, mi piace la torta di mele, sono ansioso e ho il doc"
    
    print("🧪 Test estrazione fatti corretta\n")
    print(f"Messaggio: {test_message}\n")
    
    facts = service._extract_canonical_facts(test_message)
    
    print("📝 Fatti estratti:")
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
            'user_job': '💼'
        }.get(fact_type, '📋')
        
        print(f"  {i}. {emoji} {fact_type}: {fact_value}")
    
    print(f"\n📊 Totale: {len(facts)} fatti estratti")
    
    # Verifica correzioni specifiche
    print("\n🔍 Verifica correzioni:")
    
    likes = [f for f in facts if f.startswith('user_likes:')]
    conditions = [f for f in facts if f.startswith('user_condition:')]
    
    print(f"✅ Preferenze (user_likes): {len(likes)}")
    for like in likes:
        print(f"   • {like.split(':', 1)[1]}")
    
    print(f"✅ Condizioni (user_condition): {len(conditions)}")  
    for condition in conditions:
        print(f"   • {condition.split(':', 1)[1]}")
    
    # Verifica errori precedenti
    problematic_likes = [f for f in facts if f.startswith('user_likes:') and any(x in f for x in ['sono ansioso', 'ho il doc', 'ho doc'])]
    
    if problematic_likes:
        print(f"❌ ERRORI ANCORA PRESENTI:")
        for err in problematic_likes:
            print(f"   • {err}")
    else:
        print("✅ Nessun errore trovato: stati psicologici non classificati come preferenze!")

if __name__ == "__main__":
    test_fixed_extraction()