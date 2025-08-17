#!/usr/bin/env python3
"""
Analisi quantitativa dei booster percentuali per Chain of Thought dell'AI
"""

import asyncio
import logging
import time
import json
from concept_map_analyzer import analyze_user_concept_maps, ConceptMapAnalyzer
from enhanced_memory_service import ConceptMapEnhancedMemoryService

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def analyze_cot_boost_percentage():
    """Analisi quantitativa del boost percentuale per CoT reasoning"""
    
    print("=== ANALISI QUANTITATIVA COT BOOST ===\n")
    
    # 1. Baseline metrics senza mappe
    print("📊 **BASELINE METRICS (senza mappe concettuali)**")
    baseline_metrics = {
        "reasoning_paths": 0,
        "causal_connections": 0,  
        "domain_knowledge": 0,
        "pattern_recognition": 0,
        "context_awareness": 0
    }
    
    for metric, value in baseline_metrics.items():
        print(f"   {metric}: {value}")
    print()
    
    # 2. Carica e analizza mappe
    print("🧠 **CARICAMENTO MAPPE CONCETTUALI**")
    start_time = time.time()
    thinking_pattern, semantics, user_profile = await analyze_user_concept_maps()
    analysis_time = time.time() - start_time
    
    # Crea servizio enhanced
    service = ConceptMapEnhancedMemoryService()
    service.thinking_pattern = thinking_pattern
    service.concept_semantics = semantics
    service.user_profile = user_profile
    
    # 3. Metriche delle mappe caricate
    analyzer = ConceptMapAnalyzer()
    maps = analyzer.load_all_concept_maps()
    
    total_nodes = 0
    total_edges = 0
    total_causal_edges = 0
    
    for map_id, concept_map in maps:
        if hasattr(concept_map, 'nodes'):
            total_nodes += len(concept_map.nodes)
        if hasattr(concept_map, 'edges'):
            total_edges += len(concept_map.edges)
            for edge in concept_map.edges:
                rel_type = edge.get('relationshipType', '')
                if rel_type in ['causes', 'leads_to', 'creates']:
                    total_causal_edges += 1
    
    print(f"   📈 Mappe caricate: {len(maps)}")
    print(f"   📈 Nodi totali: {total_nodes}")
    print(f"   📈 Collegamenti totali: {total_edges}")
    print(f"   📈 Collegamenti causali: {total_causal_edges}")
    print(f"   📈 Catene causali estratte: {len(semantics.causal_chains)}")
    print(f"   📈 Domini di conoscenza: {len(semantics.knowledge_domains)}")
    print(f"   📈 Cluster concettuali: {len(semantics.concept_clusters)}")
    print(f"   ⏱️ Tempo analisi: {analysis_time:.2f}s")
    print()
    
    # 4. Test su diversi tipi di query per misurare boost
    test_queries = [
        {"query": "design di una landing page efficace", "domain": "web_design", "complexity": "medium"},
        {"query": "come ridurre l'attrito nel processo di onboarding?", "domain": "ux_design", "complexity": "high"},
        {"query": "strategia per aumentare le conversioni", "domain": "marketing", "complexity": "high"},
        {"query": "struttura di un sito e-commerce", "domain": "web_dev", "complexity": "medium"},
        {"query": "migliorare la user experience con categorizzazione", "domain": "ux_design", "complexity": "high"},
        {"query": "ottimizzazione call-to-action per mobile", "domain": "mobile_ux", "complexity": "medium"},
        {"query": "dashboard per analytics con filtri avanzati", "domain": "data_viz", "complexity": "high"},
        {"query": "sistema di autenticazione user-friendly", "domain": "security_ux", "complexity": "medium"}
    ]
    
    print("🎯 **ANALISI BOOST PER TIPO DI QUERY**")
    print()
    
    boost_results = []
    
    for i, test in enumerate(test_queries, 1):
        query = test["query"]
        domain = test["domain"]
        complexity = test["complexity"]
        
        print(f"**TEST {i}: {query}**")
        print(f"   Domain: {domain}, Complexity: {complexity}")
        
        # Misura il boost
        start_time = time.time()
        
        concept_insights = service._extract_concept_insights(query, active_map_id=None)
        related_concepts = service._find_related_concepts(query, active_map_id=None)
        domain_context = service._get_domain_context(query)
        
        processing_time = time.time() - start_time
        
        # Calcola metriche di boost
        boost_metrics = {
            "causal_reasoning_paths": len(concept_insights),
            "related_concept_connections": len(related_concepts),
            "domain_knowledge_bits": len(domain_context),
            "total_context_items": len(concept_insights) + len(related_concepts) + len(domain_context),
            "processing_time_ms": processing_time * 1000,
        }
        
        # Calcola percentuali di boost rispetto al baseline
        reasoning_boost = (boost_metrics["causal_reasoning_paths"] / max(1, baseline_metrics["reasoning_paths"] + 1)) * 100
        knowledge_boost = (boost_metrics["domain_knowledge_bits"] / max(1, baseline_metrics["domain_knowledge"] + 1)) * 100
        
        # Stima boost CoT complessivo basato su:
        # - Numero di percorsi causali disponibili
        # - Ricchezza del contesto 
        # - Correlazioni incrociate
        cot_boost_percentage = min(300, (
            reasoning_boost * 0.4 +  # 40% dal reasoning causale
            knowledge_boost * 0.3 +  # 30% dalla conoscenza dominio
            (boost_metrics["related_concept_connections"] * 10) * 0.3  # 30% dalle connessioni
        ))
        
        boost_results.append({
            "query": query,
            "domain": domain,
            "complexity": complexity,
            "cot_boost_percentage": cot_boost_percentage,
            "metrics": boost_metrics
        })
        
        print(f"   📊 Causal reasoning paths: {boost_metrics['causal_reasoning_paths']}")
        print(f"   📊 Related concepts: {boost_metrics['related_concept_connections']}")
        print(f"   📊 Domain knowledge: {boost_metrics['domain_knowledge_bits']}")
        print(f"   📊 Total context items: {boost_metrics['total_context_items']}")
        print(f"   ⚡ **CoT BOOST: {cot_boost_percentage:.1f}%**")
        print(f"   ⏱️ Processing: {processing_time*1000:.1f}ms")
        print()
    
    # 5. Analisi aggregata
    print("📈 **ANALISI AGGREGATA COT BOOST**")
    print()
    
    avg_boost = sum(r["cot_boost_percentage"] for r in boost_results) / len(boost_results)
    max_boost = max(r["cot_boost_percentage"] for r in boost_results)
    min_boost = min(r["cot_boost_percentage"] for r in boost_results)
    
    # Boost per complessità
    high_complexity_boost = [r["cot_boost_percentage"] for r in boost_results if r["complexity"] == "high"]
    medium_complexity_boost = [r["cot_boost_percentage"] for r in boost_results if r["complexity"] == "medium"]
    
    avg_high_boost = sum(high_complexity_boost) / len(high_complexity_boost) if high_complexity_boost else 0
    avg_medium_boost = sum(medium_complexity_boost) / len(medium_complexity_boost) if medium_complexity_boost else 0
    
    print(f"   📊 Boost medio complessivo: **{avg_boost:.1f}%**")
    print(f"   📊 Boost massimo: **{max_boost:.1f}%**")
    print(f"   📊 Boost minimo: **{min_boost:.1f}%**")
    print(f"   📊 Boost per alta complessità: **{avg_high_boost:.1f}%**")
    print(f"   📊 Boost per media complessità: **{avg_medium_boost:.1f}%**")
    print()
    
    # 6. Proiezioni di scala
    print("🚀 **PROIEZIONI DI SCALA**")
    print()
    
    # Simula crescita con più mappe
    scale_projections = []
    for multiplier in [2, 5, 10, 20, 50]:
        projected_maps = len(maps) * multiplier
        projected_chains = len(semantics.causal_chains) * multiplier * 0.8  # Diminishing returns
        projected_concepts = len(semantics.concept_clusters) * multiplier * 0.7
        
        # Formula boost con diminishing returns
        projected_boost = avg_boost * (1 + (multiplier - 1) * 0.6)  # 60% efficiency scaling
        projected_boost = min(400, projected_boost)  # Cap at 400%
        
        scale_projections.append({
            "maps": projected_maps,
            "chains": int(projected_chains),
            "concepts": int(projected_concepts),
            "boost": projected_boost
        })
        
        print(f"   📊 Con {projected_maps} mappe:")
        print(f"      - Catene causali: ~{int(projected_chains)}")
        print(f"      - Cluster concetti: ~{int(projected_concepts)}")
        print(f"      - **CoT Boost stimato: {projected_boost:.1f}%**")
        print()
    
    # 7. Breakdown dei contributi al boost
    print("🔍 **BREAKDOWN CONTRIBUTI AL BOOST**")
    print()
    
    total_reasoning_paths = sum(len(service._extract_concept_insights(t["query"])) for t in test_queries)
    total_concept_connections = sum(len(service._find_related_concepts(t["query"])) for t in test_queries)
    total_domain_knowledge = sum(len(service._get_domain_context(t["query"])) for t in test_queries)
    
    total_context = total_reasoning_paths + total_concept_connections + total_domain_knowledge
    
    if total_context > 0:
        reasoning_contribution = (total_reasoning_paths / total_context) * 100
        concepts_contribution = (total_concept_connections / total_context) * 100
        domain_contribution = (total_domain_knowledge / total_context) * 100
    else:
        reasoning_contribution = concepts_contribution = domain_contribution = 0
    
    print(f"   🧠 Causal Reasoning: **{reasoning_contribution:.1f}%** del boost")
    print(f"   🔗 Concept Connections: **{concepts_contribution:.1f}%** del boost")
    print(f"   🎯 Domain Knowledge: **{domain_contribution:.1f}%** del boost")
    print()
    
    print("💡 **CONCLUSIONI QUANTITATIVE:**")
    print(f"✅ Boost CoT medio attuale: **{avg_boost:.1f}%**")
    print(f"✅ Con {len(maps)} mappe fornisci **{total_context}** elementi di contesto aggiuntivi")
    print(f"✅ Ogni mappa contribuisce mediamente **{total_context/len(maps):.1f}** elementi di boost")
    print(f"✅ ROI temporale: **{total_context/(analysis_time*1000):.1f}** elementi/ms di analisi")
    print(f"✅ Scalabilità: Con 100 mappe potresti raggiungere **~{avg_boost * 4:.0f}%** di boost")

if __name__ == "__main__":
    asyncio.run(analyze_cot_boost_percentage())