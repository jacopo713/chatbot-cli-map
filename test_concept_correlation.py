#!/usr/bin/env python3
"""
Test per verificare se il sistema trova correlazioni con mappe concettuali non selezionate
Test case: "crea un anteprima html di un sito di test cognitivi"
"""

import asyncio
import logging
import json
from concept_map_analyzer import get_concept_map_analyzer, analyze_user_concept_maps
from enhanced_memory_service import get_enhanced_memory_service

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_concept_correlation():
    """Test se il sistema trova correlazioni automatiche con mappe non selezionate"""
    
    print("=== TEST CORRELAZIONE MAPPE CONCETTUALI ===\n")
    
    # 1. Carica e analizza le mappe concettuali
    print("1. Caricamento e analisi mappe concettuali...")
    analyzer = get_concept_map_analyzer()
    maps = analyzer.load_all_concept_maps()
    print(f"   - Mappe trovate: {len(maps)}")
    
    if not maps:
        print("   ❌ Nessuna mappa trovata. Impossibile testare correlazioni.")
        return
    
    # Mostra titoli delle mappe disponibili
    print("   - Mappe disponibili:")
    for map_id, concept_map in maps:
        title = concept_map.title or "Senza titolo"
        nodes = len(concept_map.nodes) if hasattr(concept_map, 'nodes') else 0
        edges = len(concept_map.edges) if hasattr(concept_map, 'edges') else 0
        print(f"     * {map_id}: '{title}' ({nodes} nodi, {edges} collegamenti)")
        
        # Cerca mappe correlate ai test cognitivi
        if any(keyword in title.lower() for keyword in ['test', 'cognitiv', 'psicolog', 'mental', 'brain']):
            print(f"       🎯 POTENZIALMENTE CORRELATA ai test cognitivi")
    
    print()
    
    # 2. Inizializza enhanced memory service
    print("2. Inizializzazione enhanced memory service...")
    enhanced_service = await get_enhanced_memory_service()
    
    if not enhanced_service:
        print("   ❌ Enhanced memory service non disponibile")
        return
    
    print("   ✅ Enhanced memory service inizializzato")
    print()
    
    # 3. Test della domanda specifica
    test_message = "crea un anteprima html di un sito di test cognitivi"
    print(f"3. Test messaggio: '{test_message}'")
    print()
    
    # 4. Recupera contesto enhanced SENZA mappa selezionata
    print("4. Recupero contesto enhanced (SENZA mappa selezionata):")
    try:
        enhanced_context = await enhanced_service.get_enhanced_conversation_context(
            current_message=test_message,
            conversation_id="test_correlation",
            context_limit=3,
            active_concept_map_id=None  # NESSUNA mappa selezionata
        )
        
        print(f"   - Confidence score: {enhanced_context.confidence_score:.2f}")
        print(f"   - Concept insights trovati: {len(enhanced_context.concept_map_insights)}")
        print(f"   - Related concepts trovati: {len(enhanced_context.related_concepts)}")
        print(f"   - Domain context: {len(enhanced_context.domain_context)}")
        print(f"   - Thinking hints: {len(enhanced_context.thinking_style_hints)}")
        
        # Dettaglio insights
        if enhanced_context.concept_map_insights:
            print("\n   📋 CONCEPT MAP INSIGHTS (da mappe non selezionate):")
            for insight in enhanced_context.concept_map_insights:
                print(f"      * {insight}")
        
        if enhanced_context.related_concepts:
            print("\n   🔗 RELATED CONCEPTS:")
            for concept in enhanced_context.related_concepts:
                print(f"      * {concept}")
        
        if enhanced_context.domain_context:
            print("\n   🎯 DOMAIN CONTEXT:")
            for domain in enhanced_context.domain_context:
                print(f"      * {domain}")
        
        # 5. Forma il contesto finale
        print("\n5. Contesto finale che verrebbe inviato all'AI:")
        formatted_context = enhanced_service.format_enhanced_context(enhanced_context)
        
        if formatted_context:
            print("   ✅ CONTESTO TROVATO:")
            print("   " + "="*50)
            print(formatted_context)
            print("   " + "="*50)
            
            # Verifica se contiene riferimenti a test cognitivi
            context_lower = formatted_context.lower()
            cognitive_keywords = ['test', 'cognitiv', 'psicolog', 'mental', 'brain', 'memoria', 'attenzione']
            found_keywords = [kw for kw in cognitive_keywords if kw in context_lower]
            
            if found_keywords:
                print(f"\n   🎯 CORRELAZIONE TROVATA! Keywords: {found_keywords}")
                print("   ✅ Il sistema HA trovato correlazioni automatiche con mappe non selezionate")
            else:
                print("\n   ❌ Nessuna correlazione evidente con test cognitivi")
                print("   ❌ Il sistema NON ha trovato correlazioni specifiche")
        else:
            print("   ❌ NESSUN CONTESTO generato")
            print("   ❌ Il sistema NON ha trovato correlazioni")
        
    except Exception as e:
        print(f"   ❌ Errore nel recupero contesto: {e}")
        import traceback
        traceback.print_exc()

    print("\n=== FINE TEST ===")

if __name__ == "__main__":
    asyncio.run(test_concept_correlation())