#!/usr/bin/env python3
"""Debug script per verificare cosa è salvato su Pinecone"""

import asyncio
import os
import sys
sys.path.append(os.path.dirname(__file__))

from pinecone import Pinecone
from dotenv import load_dotenv

async def debug_pinecone_memories():
    """Verifica cosa è salvato su Pinecone"""
    load_dotenv()
    
    api_key = os.getenv("PINECONE_API_KEY")
    index_name = os.getenv("PINECONE_INDEX", "chatbot-cli-map")
    host = os.getenv("PINECONE_HOST", "https://chatbot-cli-map-mp69iv8.svc.aped-4627-b74a.pinecone.io")
    
    if not api_key:
        print("❌ PINECONE_API_KEY non trovata")
        return
    
    try:
        print("🔍 Connessione a Pinecone...")
        pinecone_client = Pinecone(api_key=api_key)
        index = pinecone_client.Index(name=index_name, host=host)
        
        # Recupera statistiche dell'index
        stats = await asyncio.to_thread(index.describe_index_stats)
        print(f"📊 Statistiche index: {stats.get('total_vector_count', 0)} vettori totali")
        
        # Cerca memorie recenti con contenuti specifici
        search_terms = ["gelato", "limone", "fragole", "freestyle"]
        
        for term in search_terms:
            print(f"\n🔍 Cercando '{term}'...")
            
            # Query senza embedding - usa fetch se abbiamo ID o query con filtri
            try:
                # Prova con una query molto permissiva
                results = await asyncio.to_thread(
                    index.query,
                    vector=[0.0] * 1024,  # Vector dummy
                    filter={"message_type": "personal"},
                    top_k=20,
                    include_metadata=True
                )
                
                found = False
                for match in results.matches:
                    content = match.metadata.get("content", "").lower()
                    if term in content:
                        found = True
                        print(f"  ✅ Trovato: ID={match.id}")
                        print(f"     Content: {match.metadata.get('content', 'N/A')}")
                        print(f"     Message_type: {match.metadata.get('message_type', 'N/A')}")
                        print(f"     Category: {match.metadata.get('category', 'N/A')}")
                        print(f"     Fact_type: {match.metadata.get('fact_type', 'N/A')}")
                        print(f"     Role: {match.metadata.get('role', 'N/A')}")
                        print(f"     Timestamp: {match.metadata.get('timestamp', 'N/A')}")
                        print(f"     Scope: {match.metadata.get('scope', 'N/A')}")
                        print(f"     Conversation_id: {match.metadata.get('conversation_id', 'N/A')}")
                        print("     ---")
                
                if not found:
                    print(f"  ❌ Nessun risultato per '{term}'")
                    
            except Exception as e:
                print(f"  ❌ Errore nella ricerca per '{term}': {e}")
        
        # Mostra tutte le memorie personal recenti
        print(f"\n📋 Tutte le memorie 'personal' recenti:")
        try:
            all_personal = await asyncio.to_thread(
                index.query,
                vector=[0.0] * 1024,
                filter={"message_type": "personal"},
                top_k=10,
                include_metadata=True
            )
            
            for i, match in enumerate(all_personal.matches, 1):
                print(f"\n{i}. ID: {match.id}")
                print(f"   Content: {match.metadata.get('content', 'N/A')}")
                print(f"   Message_type: {match.metadata.get('message_type', 'N/A')}")
                print(f"   Category: {match.metadata.get('category', 'N/A')}")
                print(f"   Fact_type: {match.metadata.get('fact_type', 'N/A')}")
                print(f"   Timestamp: {match.metadata.get('timestamp', 'N/A')}")
                
        except Exception as e:
            print(f"❌ Errore nel recupero memorie personal: {e}")
    
    except Exception as e:
        print(f"❌ Errore generale: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_pinecone_memories())