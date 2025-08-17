#!/usr/bin/env python3
"""
Test diretto delle correlazioni concettuali senza dipendenze dai servizi di memoria
"""

import asyncio
import logging
from concept_map_analyzer import ConceptMapAnalyzer, analyze_user_concept_maps
from enhanced_memory_service import ConceptMapEnhancedMemoryService

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_direct_correlation():
    """Test diretto delle correlazioni"""
    
    print("=== TEST CORRELAZIONE DIRETTA ===\n")
    
    # 1. Analizza le mappe concettuali
    print("1. Analisi mappe concettuali...")
    thinking_pattern, semantics, user_profile = await analyze_user_concept_maps()
    
    print(f"   - Knowledge domains: {len(semantics.knowledge_domains)}")
    print(f"   - Concept clusters: {len(semantics.concept_clusters)}")
    print(f"   - Causal chains: {len(semantics.causal_chains)}")
    print(f"   - Hierarchical trees: {len(semantics.hierarchical_trees)}")
    print()
    
    # 2. Crea il servizio enhanced senza inizializzazione completa
    print("2. Creazione servizio enhanced...")
    service = ConceptMapEnhancedMemoryService()
    service.thinking_pattern = thinking_pattern
    service.concept_semantics = semantics
    service.user_profile = user_profile
    print("   ✅ Servizio creato con analisi delle mappe")
    print()
    
    # 3. Test della correlazione
    test_message = "crea un anteprima html di un sito di test cognitivi"
    print(f"3. Test messaggio: '{test_message}'")
    print()
    
    # 4. Estrai insights dalle mappe (SENZA mappa selezionata)
    print("4. Estrazione insights da mappe NON selezionate:")
    concept_insights = service._extract_concept_insights(test_message, active_map_id=None)
    
    print(f"   - Concept insights trovati: {len(concept_insights)}")
    if concept_insights:
        print("   📋 INSIGHTS TROVATI:")
        for insight in concept_insights:
            print(f"      * {insight}")
    else:
        print("   ❌ Nessun insight trovato")
    print()
    
    # 5. Trova concetti correlati
    print("5. Ricerca concetti correlati:")
    related_concepts = service._find_related_concepts(test_message, active_map_id=None)
    
    print(f"   - Related concepts trovati: {len(related_concepts)}")
    if related_concepts:
        print("   🔗 RELATED CONCEPTS:")
        for concept in related_concepts:
            print(f"      * {concept}")
    else:
        print("   ❌ Nessun concetto correlato trovato")
    print()
    
    # 6. Verifica contesto dominio
    print("6. Verifica contesto dominio:")
    domain_context = service._get_domain_context(test_message)
    
    print(f"   - Domain context trovato: {len(domain_context)}")
    if domain_context:
        print("   🎯 DOMAIN CONTEXT:")
        for context in domain_context:
            print(f"      * {context}")
    else:
        print("   ❌ Nessun contesto dominio trovato")
    print()
    
    # 7. Analisi manuale keyword matching
    print("7. Analisi manuale keyword matching:")
    message_lower = test_message.lower()
    
    # Cerca manualmente nelle mappe
    analyzer = ConceptMapAnalyzer()
    maps = analyzer.load_all_concept_maps()
    
    correlations_found = []
    
    for map_id, concept_map in maps:
        title_lower = (concept_map.title or "").lower()
        
        # Check title correlations
        test_keywords = ['test', 'cognitiv', 'html', 'sito', 'web']
        title_matches = [kw for kw in test_keywords if kw in title_lower]
        
        # Check node labels
        node_matches = []
        if hasattr(concept_map, 'nodes'):
            for node in concept_map.nodes:
                label_lower = (node.get('label', '') or '').lower()
                matches = [kw for kw in test_keywords if kw in label_lower]
                if matches:
                    node_matches.extend(matches)
        
        if title_matches or node_matches:
            correlations_found.append({
                'map_id': map_id,
                'title': concept_map.title,
                'title_matches': title_matches,
                'node_matches': list(set(node_matches))
            })
    
    if correlations_found:
        print("   ✅ CORRELAZIONI TROVATE manualmente:")
        for corr in correlations_found:
            print(f"      * Mappa: {corr['title']}")
            print(f"        - ID: {corr['map_id']}")
            if corr['title_matches']:
                print(f"        - Title matches: {corr['title_matches']}")
            if corr['node_matches']:
                print(f"        - Node matches: {corr['node_matches']}")
    else:
        print("   ❌ Nessuna correlazione trovata manualmente")
    
    print("\n=== RISULTATO FINALE ===")
    
    total_insights = len(concept_insights) + len(related_concepts) + len(domain_context)
    
    if total_insights > 0 or correlations_found:
        print("✅ SUCCESSO: Il sistema TROVA correlazioni con mappe non selezionate")
        print(f"   - {len(concept_insights)} concept insights")
        print(f"   - {len(related_concepts)} related concepts")  
        print(f"   - {len(domain_context)} domain contexts")
        print(f"   - {len(correlations_found)} correlazioni manuali trovate")
        
        if correlations_found:
            print("\n📋 MAPPE CORRELATE che potrebbero essere inviate nel contesto:")
            for corr in correlations_found:
                print(f"   * {corr['title']} (keywords: {corr['title_matches'] + corr['node_matches']})")
    else:
        print("❌ FALLIMENTO: Il sistema NON trova correlazioni automatiche")
        print("   Questo significa che per domande come 'test cognitivi' non viene")
        print("   inviato automaticamente contesto da mappe correlate non selezionate")

    print("\n=== FINE TEST ===")

if __name__ == "__main__":
    asyncio.run(test_direct_correlation())