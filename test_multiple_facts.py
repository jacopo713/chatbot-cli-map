#!/usr/bin/env python3
"""
Test script per verificare l'estrazione di multiple informazioni personali
"""
import asyncio
import os
from hybrid_memory_service import HybridMemoryService, HybridMemoryConfig

async def test_multiple_facts_extraction():
    """Test l'estrazione di multiple informazioni da un singolo messaggio"""
    
    # Configurazione del servizio (usa le variabili di ambiente)
    config = HybridMemoryConfig(
        cohere_api_key=os.getenv("COHERE_API_KEY", ""),
        pinecone_api_key=os.getenv("PINECONE_API_KEY", ""),
        pinecone_index_name=os.getenv("PINECONE_INDEX", "chatbot-cli-map"),
        pinecone_host=os.getenv("PINECONE_HOST", "https://chatbot-cli-map-mp69iv8.svc.aped-4627-b74a.pinecone.io")
    )
    
    if not config.cohere_api_key or not config.pinecone_api_key:
        print("❌ API keys non configurate. Salto il test.")
        return
    
    # Inizializza il servizio
    service = HybridMemoryService(config)
    await service.initialize()
    
    # Test message da Jacopo
    test_message = "mi chiamo jacopo e ho 29 anni, vivo a brovello carpugnino, e mi piacciono i gatti e cani ma non faccio distinzioni mi piacciono tutti gli animali e tutti andrebbero rispettati"
    
    print("🔍 Test dell'estrazione di fatti multipli:")
    print(f"Messaggio originale: {test_message}")
    print()
    
    # Test del metodo di estrazione fatti
    facts = service._extract_canonical_facts(test_message)
    
    print("📝 Fatti estratti:")
    for i, fact in enumerate(facts, 1):
        print(f"  {i}. {fact}")
    
    print()
    
    # Test dello storage completo
    print("💾 Test dello storage...")
    success = await service.store_conversation_turn(
        user_message=test_message,
        ai_response="Ciao Jacopo! È bello conoscerti. Capisco che ami tutti gli animali e rispetti molto la vita animale.",
        conversation_id="test-multiple-facts",
        additional_metadata={"test": True}
    )
    
    print(f"Storage completato: {'✅' if success else '❌'}")
    
    # Test della ricerca per verificare che le informazioni siano state memorizzate
    print("\n🔎 Test della ricerca delle informazioni memorizzate...")
    
    # Cerchiamo diverse informazioni
    searches = [
        "jacopo",
        "29 anni", 
        "brovello carpugnino",
        "animali",
        "gatti e cani"
    ]
    
    for search_term in searches:
        results = await service.retrieve_memories(
            query=search_term,
            conversation_id="test-multiple-facts",
            limit=3
        )
        
        print(f"\nRicerca per '{search_term}':")
        if results:
            for result in results:
                content = result.get('content', '')[:100] + '...' if len(result.get('content', '')) > 100 else result.get('content', '')
                score = result.get('score', 0)
                print(f"  - {content} (score: {score:.3f})")
        else:
            print("  - Nessun risultato trovato")
    
    # Stats del servizio
    stats = service.get_stats()
    print(f"\n📊 Statistiche del servizio:")
    for key, value in stats.items():
        print(f"  {key}: {value}")

if __name__ == "__main__":
    asyncio.run(test_multiple_facts_extraction())