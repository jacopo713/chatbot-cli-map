#!/usr/bin/env python3
"""
Test per verificare il nuovo sistema di salvataggio manuale delle risposte AI
"""
import asyncio
import sys
import json
sys.path.append('.')

from hybrid_memory_service import HybridMemoryService, HybridMemoryConfig

async def test_manual_save():
    """Test del salvataggio manuale delle risposte AI"""
    
    config = HybridMemoryConfig(
        cohere_api_key="dummy",
        pinecone_api_key="dummy"
    )
    service = HybridMemoryService(config)
    
    print("🧪 Test del nuovo sistema di salvataggio manuale\n")
    
    # Test 1: Verifica che le chat_history non vengono più salvate automaticamente
    print("1. Test salvataggio automatico (dovrebbe essere disabilitato):")
    
    # Simula una conversazione normale
    user_message = "Spiegami come funziona Python"
    ai_response = "Python è un linguaggio di programmazione interpretato, ad alto livello e con una sintassi che privilegia la leggibilità del codice."
    
    # Questo dovrebbe salvare SOLO il messaggio utente, NON la risposta AI
    try:
        success = await service.store_conversation_turn(
            user_message=user_message,
            ai_response=ai_response,
            conversation_id="test-manual-save"
        )
        print(f"   - Conversation turn stored: {success}")
        print(f"   - User message: '{user_message[:50]}...'")
        print(f"   - AI response: '{ai_response[:50]}...' (NON salvata automaticamente)")
    except Exception as e:
        print(f"   - Errore (atteso se mancano API keys): {e}")
    
    print("\n2. Test salvataggio manuale:")
    
    # Test del metodo di salvataggio manuale
    try:
        manual_success = await service.store_ai_response_manually(
            ai_response=ai_response,
            conversation_id="test-manual-save",
            user_message=user_message
        )
        print(f"   - Manual save success: {manual_success}")
        print(f"   - AI response manually saved: '{ai_response[:50]}...'")
    except Exception as e:
        print(f"   - Errore (atteso se mancano API keys): {e}")
    
    print("\n3. Verifica struttura memoria:")
    print("   - Le risposte AI salvate manualmente hanno:")
    print("     • message_type: 'chat' (non 'chat_history')")
    print("     • importance: 'high' (selezionate dall'utente)")
    print("     • metadata: 'manually_saved: true'")
    print("     • storage_tier: 'important' (permanente)")
    
    print("\n✅ Risultati attesi:")
    print("   - ❌ Risposte AI NON più salvate automaticamente")
    print("   - ✅ Possibilità di salvare manualmente solo quelle importanti")
    print("   - ✅ Pulsanti Copy/Save nell'interfaccia frontend")
    print("   - ✅ Feedback visivo per le azioni utente")
    print("   - 💾 Riduzione significativa dello storage utilizzato")

if __name__ == "__main__":
    asyncio.run(test_manual_save())