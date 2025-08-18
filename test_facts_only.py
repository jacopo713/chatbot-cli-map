#!/usr/bin/env python3
"""
Test script per verificare solo l'estrazione di multiple informazioni personali
(senza richiedere API keys esterne)
"""
import sys
sys.path.append('.')

from hybrid_memory_service import MessageImportanceClassifier, HybridMemoryService, HybridMemoryConfig

def test_facts_extraction_only():
    """Test solo l'estrazione di multiple informazioni da un singolo messaggio"""
    
    # Crea un'istanza fittizia del servizio per testare l'estrazione
    config = HybridMemoryConfig(
        cohere_api_key="dummy",
        pinecone_api_key="dummy"
    )
    service = HybridMemoryService(config)
    
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
    
    # Test che il metodo contenga informazioni personali
    is_personal = service._contains_personal_info(test_message)
    print(f"Contiene informazioni personali: {'✅ Sì' if is_personal else '❌ No'}")
    
    # Test del classificatore di importanza
    classifier = MessageImportanceClassifier()
    importance, score, reasoning = classifier.classify(test_message)
    print(f"Importanza: {importance.value} (score: {score:.3f})")
    print(f"Fattori: {reasoning.get('factors', [])}")
    
    # Verifica che abbiamo estratto multiple informazioni
    expected_types = ['user_name', 'user_age', 'user_location', 'user_likes']
    found_types = [fact.split(':')[0] for fact in facts if ':' in fact]
    
    print(f"\nTipi di informazione trovati: {found_types}")
    print(f"Tipi attesi: {expected_types}")
    
    missing_types = [t for t in expected_types if t not in found_types]
    if missing_types:
        print(f"⚠️  Tipi mancanti: {missing_types}")
    else:
        print("✅ Tutti i tipi attesi sono stati trovati!")
    
    print(f"\nNumero di fatti estratti: {len(facts)}")
    print("✅ Test completato!" if len(facts) > 1 else "❌ Non sono stati estratti abbastanza fatti")

if __name__ == "__main__":
    test_facts_extraction_only()