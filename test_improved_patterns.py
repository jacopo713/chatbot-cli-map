#!/usr/bin/env python3
"""
Test dei pattern migliorati per info personali
"""
import sys
sys.path.append('.')

from hybrid_memory_service import HybridMemoryService, HybridMemoryConfig

def test_improved_patterns():
    """Test che i nuovi pattern riconoscano info mediche e fisiche"""
    
    config = HybridMemoryConfig(
        cohere_api_key="dummy",
        pinecone_api_key="dummy"
    )
    service = HybridMemoryService(config)
    
    print("🔍 Test pattern MIGLIORATI per info personali")
    print("="*50)
    
    test_cases = [
        # Casi che PRIMA fallivano
        ("ho l'anemia mediterranea", True, "Medical condition"),
        ("sono alto 174 cm", True, "Physical characteristic"),
        ("soffro di ansia", True, "Health condition"),
        ("ho problemi di sonno", True, "Health issue"),
        ("peso 70 kg", True, "Physical measure"),
        
        # Casi che dovevano GIÀ funzionare
        ("mi chiamo jacopo", True, "Name"),
        ("vivo a milano", True, "Location"),
        ("mi piace il calcio", True, "Preference"),
        ("ho 29 anni", True, "Age"),
        
        # Casi che NON dovrebbero essere personali
        ("che tempo fa?", False, "Weather question"),
        ("come stai?", False, "Greeting question"),
        ("grazie", False, "Thank you"),
        
        # Edge cases medici
        ("ho il diabete", True, "Medical condition"),
        ("prendo farmaci per l'ansia", True, "Medical treatment"),
        ("vado in terapia", False, "NOT matched - 'sono in terapia' would match"),
        ("sono in terapia", True, "Medical treatment"),
    ]
    
    for message, expected, description in test_cases:
        result = service._contains_personal_info(message)
        status = "✅" if result == expected else "❌"
        
        print(f"{status} \"{message}\" → {result} (expected: {expected}) - {description}")
        
        if result != expected:
            print(f"    🚨 FAILED: Expected {expected}, got {result}")
    
    print(f"\n" + "="*50)
    print("✅ Test pattern completato!")

if __name__ == "__main__":
    test_improved_patterns()