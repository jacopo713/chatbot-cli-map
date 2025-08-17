#!/usr/bin/env python3
"""Test script per verificare la nuova categorizzazione delle memorie"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(__file__))

from memory_service import initialize_memory_service

async def test_categorization():
    """Test della nuova categorizzazione"""
    print("Inizializzazione del servizio di memoria...")
    
    try:
        memory_service = await initialize_memory_service()
        if not memory_service:
            print("❌ Servizio memoria non disponibile (API keys mancanti)")
            return
        
        # Test messages con diverse categorie
        test_messages = [
            ("Mi chiamo Jacopo", "personal"),
            ("Ho 29 anni", "personal"), 
            ("Abito a Brovello Carpugnino", "personal"),
            ("Lavoro come sviluppatore", "work"),
            ("Mi piace la canoa", "hobby"),
            ("Ho l'anemia mediterranea", "health"),
            ("Soffro di ansia", "health"),
            ("Ho il disturbo ossessivo compulsivo", "health")
        ]
        
        print("\n🧪 Testing categorization...")
        
        for message, expected_category in test_messages:
            print(f"\nTest: '{message}'")
            
            # Test della funzione di categorizzazione
            fact, category = await memory_service._extract_canonical_facts(message)
            print(f"  Fatto estratto: {fact}")
            print(f"  Categoria: {category} (attesa: {expected_category})")
            
            # Verifica se la categoria è corretta
            if category == expected_category:
                print("  ✅ Categoria corretta")
            else:
                print(f"  ⚠️  Categoria diversa da quella attesa")
        
        print("\n✅ Test completato!")
        
    except Exception as e:
        print(f"❌ Errore durante il test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_categorization())