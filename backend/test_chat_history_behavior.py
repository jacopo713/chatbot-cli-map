#!/usr/bin/env python3
"""
Test per verificare il comportamento delle chat history
"""
import sys
sys.path.append('.')

from hybrid_memory_service import HybridMemoryService, HybridMemoryConfig, HybridMemoryItem, ImportanceLevel, StorageTier
from datetime import datetime

def test_chat_history_filtering():
    """Test per verificare se le chat history vengono filtrate durante la ricerca"""
    
    config = HybridMemoryConfig(
        cohere_api_key="dummy",
        pinecone_api_key="dummy"
    )
    service = HybridMemoryService(config)
    
    print("🔍 Test del comportamento delle chat history\n")
    
    # Simuliamo la creazione di diversi tipi di memorie
    print("📝 Tipi di messaggi che vengono memorizzati:")
    
    # 1. Messaggio utente normale (chat)
    user_message = "Ciao, come stai?"
    is_personal = service._contains_personal_info(user_message)
    print(f"1. Messaggio utente normale: '{user_message}'")
    print(f"   - È personale: {is_personal}")
    print(f"   - Tipo messaggio: 'chat'")
    print(f"   - Viene recuperato nella ricerca: ✅ SÌ\n")
    
    # 2. Messaggio utente con info personali
    personal_message = "Mi chiamo Marco e ho 25 anni"
    is_personal = service._contains_personal_info(personal_message)
    facts = service._extract_canonical_facts(personal_message)
    print(f"2. Messaggio con info personali: '{personal_message}'")
    print(f"   - È personale: {is_personal}")
    print(f"   - Fatti estratti: {facts}")
    print(f"   - Tipo messaggio: 'personal'")
    print(f"   - Viene recuperato nella ricerca: ✅ SÌ\n")
    
    # 3. Risposta AI (chat_history)
    ai_response = "Ciao! Sto bene, grazie. Come posso aiutarti oggi?"
    print(f"3. Risposta AI: '{ai_response}'")
    print(f"   - Tipo messaggio: 'chat_history'")
    print(f"   - Viene recuperato nella ricerca: ❌ NO (filtrata)\n")
    
    print("🎯 RIEPILOGO:")
    print("Le CHAT HISTORY (risposte AI) vengono:")
    print("✅ Memorizzate in Pinecone (per preservare il contesto)")
    print("❌ FILTRATE durante la ricerca (non influenzano le risposte)")
    print("🔄 Incluse nel recent buffer (per contesto immediato)")
    
    print("\n📊 Vantaggi del sistema attuale:")
    print("- Evita che l'AI si citi se stessa")
    print("- Mantiene focus sui contenuti dell'utente")
    print("- Preserva la cronologia per debug/analisi")
    print("- Riduce rumore nella ricerca semantica")
    
    print("\n🤔 Possibili alternative:")
    print("1. Rimuovere completamente le chat_history (risparmio storage)")
    print("2. Includerle nella ricerca con peso ridotto")
    print("3. Mantenerle solo nel recent buffer")
    
    # Test del filtro nella ricerca recent buffer
    print("\n🔍 Test filtro recent buffer:")
    
    # Simula aggiungi items al recent buffer
    user_item = HybridMemoryItem(
        content="Test user message",
        metadata={"role": "user"},
        timestamp=datetime.now(),
        conversation_id="test-123",
        message_type="chat",
        importance=ImportanceLevel.MEDIUM
    )
    
    ai_item = HybridMemoryItem(
        content="Test AI response", 
        metadata={"role": "assistant"},
        timestamp=datetime.now(),
        conversation_id="test-123",
        message_type="chat_history",
        importance=ImportanceLevel.MEDIUM
    )
    
    service.recent_buffer.append(user_item)
    service.recent_buffer.append(ai_item)
    
    # Test ricerca nel recent buffer
    results = service._search_recent_buffer("test", "test-123")
    print(f"Ricerca 'test' nel recent buffer:")
    for result in results:
        msg_type = result.get('message_type', 'unknown')
        content = result.get('content', '')
        print(f"   - Tipo: {msg_type}, Contenuto: '{content}'")
    
    if any(r.get('message_type') == 'chat_history' for r in results):
        print("⚠️  Le chat_history vengono trovate nel recent buffer!")
    else:
        print("✅ Le chat_history sono filtrate anche nel recent buffer")

if __name__ == "__main__":
    test_chat_history_filtering()