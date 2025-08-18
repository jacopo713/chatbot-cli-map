#!/usr/bin/env python3
"""
Test script for the enhanced memory system with concept map integration
"""

import asyncio
import logging
import json
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_concept_map_analysis():
    """Test concept map analysis functionality"""
    logger.info("🧪 Testing Concept Map Analysis...")
    
    try:
        from concept_map_analyzer import analyze_user_concept_maps, get_concept_map_analyzer
        
        # Test analyzer initialization
        analyzer = get_concept_map_analyzer()
        logger.info(f"✅ Concept Map Analyzer initialized: {type(analyzer).__name__}")
        
        # Load and analyze concept maps
        concept_maps = analyzer.load_all_concept_maps()
        logger.info(f"📊 Loaded {len(concept_maps)} concept maps")
        
        if concept_maps:
            # Analyze thinking patterns
            thinking_pattern = analyzer.analyze_thinking_patterns(concept_maps)
            logger.info(f"🧠 Thinking Pattern Analysis:")
            logger.info(f"   - Concept granularity: {thinking_pattern.concept_granularity:.1f}")
            logger.info(f"   - Connection density: {thinking_pattern.connection_density:.2f}")
            logger.info(f"   - Hierarchical preference: {thinking_pattern.hierarchical_preference:.2f}")
            logger.info(f"   - Causal preference: {thinking_pattern.causal_preference:.2f}")
            logger.info(f"   - Top relationship types: {list(thinking_pattern.preferred_relationship_types.keys())[:3]}")
            
            # Analyze semantic metadata
            semantics = analyzer.extract_semantic_metadata(concept_maps)
            logger.info(f"🔗 Semantic Analysis:")
            logger.info(f"   - Concept clusters: {len(semantics.concept_clusters)}")
            logger.info(f"   - Causal chains: {len(semantics.causal_chains)}")
            logger.info(f"   - Hierarchical trees: {len(semantics.hierarchical_trees)}")
            logger.info(f"   - Knowledge domains: {list(semantics.knowledge_domains)[:5]}")
            
            # Generate user profile
            user_profile = analyzer.generate_user_profile(thinking_pattern, semantics)
            logger.info(f"👤 User Profile Generated:")
            logger.info(f"   - Thinking style: {user_profile.get('thinking_style', {})}")
            logger.info(f"   - Knowledge domains: {user_profile.get('knowledge_domains', [])}")
            logger.info(f"   - Reasoning patterns: {user_profile.get('reasoning_patterns', {})}")
            
            return True
        else:
            logger.warning("⚠️ No concept maps found for analysis")
            return False
            
    except Exception as e:
        logger.error(f"❌ Concept map analysis failed: {e}")
        return False

async def test_enhanced_memory_service():
    """Test enhanced memory service functionality"""
    logger.info("🧪 Testing Enhanced Memory Service...")
    
    try:
        from enhanced_memory_service import ConceptMapEnhancedMemoryService
        
        # Initialize enhanced memory service
        enhanced_service = ConceptMapEnhancedMemoryService()
        success = await enhanced_service.initialize()
        
        if not success:
            logger.warning("⚠️ Enhanced memory service failed to initialize (likely missing API keys)")
            return False
        
        logger.info("✅ Enhanced Memory Service initialized successfully")
        
        # Test enhanced context generation
        test_message = "Come posso migliorare le performance del mio codice Python?"
        conversation_id = "test_conversation"
        
        enhanced_context = await enhanced_service.get_enhanced_conversation_context(
            test_message, conversation_id, context_limit=3
        )
        
        logger.info(f"🚀 Enhanced Context Generated:")
        logger.info(f"   - Confidence score: {enhanced_context.confidence_score:.2f}")
        logger.info(f"   - Concept insights: {len(enhanced_context.concept_map_insights)}")
        logger.info(f"   - Thinking hints: {len(enhanced_context.thinking_style_hints)}")
        logger.info(f"   - Related concepts: {len(enhanced_context.related_concepts)}")
        logger.info(f"   - Domain context: {len(enhanced_context.domain_context)}")
        
        # Test context formatting
        formatted_context = enhanced_service.format_enhanced_context(enhanced_context)
        if formatted_context:
            logger.info(f"📝 Formatted Context (first 200 chars):")
            logger.info(f"   {formatted_context[:200]}...")
        
        # Test stats
        stats = enhanced_service.get_stats()
        logger.info(f"📊 Enhanced Service Stats:")
        for key, value in stats.items():
            logger.info(f"   - {key}: {value}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Enhanced memory service test failed: {e}")
        return False

async def test_sample_concept_maps():
    """Test with sample concept maps if none exist"""
    logger.info("🧪 Testing with Sample Concept Maps...")
    
    concept_maps_dir = Path("backend/concept_maps")
    
    # Check if we have concept maps
    if not concept_maps_dir.exists() or len(list(concept_maps_dir.glob("*.json"))) == 0:
        logger.info("📝 Creating sample concept maps for testing...")
        
        # Create directory if it doesn't exist
        concept_maps_dir.mkdir(parents=True, exist_ok=True)
        
        # Sample concept map 1: Programming concepts
        sample_map_1 = {
            "title": "Python Programming Concepts",
            "nodes": [
                {"id": "python", "label": "Python", "x": 100, "y": 100},
                {"id": "functions", "label": "Functions", "x": 300, "y": 100},
                {"id": "performance", "label": "Performance", "x": 500, "y": 100},
                {"id": "optimization", "label": "Optimization", "x": 700, "y": 100}
            ],
            "edges": [
                {"id": "e1", "from": "python", "to": "functions", "relationshipType": "has"},
                {"id": "e2", "from": "functions", "to": "performance", "relationshipType": "affects"},
                {"id": "e3", "from": "performance", "to": "optimization", "relationshipType": "needs"}
            ]
        }
        
        # Sample concept map 2: Learning concepts
        sample_map_2 = {
            "title": "Learning and Development",
            "nodes": [
                {"id": "learning", "label": "Learning", "x": 100, "y": 100},
                {"id": "practice", "label": "Practice", "x": 300, "y": 100},
                {"id": "skill", "label": "Skill Development", "x": 500, "y": 100},
                {"id": "mastery", "label": "Mastery", "x": 700, "y": 100}
            ],
            "edges": [
                {"id": "e1", "from": "learning", "to": "practice", "relationshipType": "leads_to"},
                {"id": "e2", "from": "practice", "to": "skill", "relationshipType": "creates"},
                {"id": "e3", "from": "skill", "to": "mastery", "relationshipType": "leads_to"}
            ]
        }
        
        # Save sample maps
        with open(concept_maps_dir / "sample_programming.json", 'w') as f:
            json.dump(sample_map_1, f, indent=2)
        
        with open(concept_maps_dir / "sample_learning.json", 'w') as f:
            json.dump(sample_map_2, f, indent=2)
        
        logger.info("✅ Sample concept maps created")
        return True
    else:
        logger.info(f"✅ Found {len(list(concept_maps_dir.glob('*.json')))} existing concept maps")
        return True

async def test_integration_scenarios():
    """Test integration scenarios"""
    logger.info("🧪 Testing Integration Scenarios...")
    
    test_scenarios = [
        {
            "message": "Come posso ottimizzare il mio codice Python?",
            "expected_domains": ["programming", "technical"],
            "expected_concepts": ["python", "optimization", "performance"]
        },
        {
            "message": "Voglio migliorare le mie competenze di programmazione",
            "expected_domains": ["learning", "programming"],
            "expected_concepts": ["skill", "learning", "practice"]
        },
        {
            "message": "Quali sono le best practice per lo sviluppo web?",
            "expected_domains": ["web_development", "programming"],
            "expected_concepts": ["web", "development", "best practice"]
        }
    ]
    
    try:
        from enhanced_memory_service import ConceptMapEnhancedMemoryService
        
        enhanced_service = ConceptMapEnhancedMemoryService()
        success = await enhanced_service.initialize()
        
        if not success:
            logger.warning("⚠️ Cannot test integration scenarios - enhanced service not available")
            return False
        
        for i, scenario in enumerate(test_scenarios, 1):
            logger.info(f"🔍 Scenario {i}: {scenario['message'][:50]}...")
            
            enhanced_context = await enhanced_service.get_enhanced_conversation_context(
                scenario['message'], f"test_scenario_{i}", context_limit=3
            )
            
            logger.info(f"   📊 Results:")
            logger.info(f"   - Confidence: {enhanced_context.confidence_score:.2f}")
            logger.info(f"   - Insights: {enhanced_context.concept_map_insights}")
            logger.info(f"   - Style hints: {enhanced_context.thinking_style_hints}")
            logger.info(f"   - Related concepts: {enhanced_context.related_concepts}")
            logger.info(f"   - Domain context: {enhanced_context.domain_context}")
            
        return True
        
    except Exception as e:
        logger.error(f"❌ Integration scenario test failed: {e}")
        return False

async def main():
    """Main test function"""
    logger.info("🚀 Starting Enhanced Memory System Tests")
    logger.info("=" * 60)
    
    test_results = {}
    
    # Test 1: Sample concept maps creation
    test_results["sample_maps"] = await test_sample_concept_maps()
    
    # Test 2: Concept map analysis
    test_results["concept_analysis"] = await test_concept_map_analysis()
    
    # Test 3: Enhanced memory service
    test_results["enhanced_memory"] = await test_enhanced_memory_service()
    
    # Test 4: Integration scenarios
    test_results["integration"] = await test_integration_scenarios()
    
    # Summary
    logger.info("=" * 60)
    logger.info("📋 TEST RESULTS SUMMARY:")
    
    passed = 0
    total = len(test_results)
    
    for test_name, result in test_results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        logger.info(f"   {test_name}: {status}")
        if result:
            passed += 1
    
    logger.info(f"\n🏆 Overall: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 All tests passed! Enhanced memory system is ready!")
    elif passed > 0:
        logger.info("⚠️ Some tests passed. Check logs for issues.")
    else:
        logger.info("❌ All tests failed. Check configuration and dependencies.")
    
    return passed == total

if __name__ == "__main__":
    import sys
    sys.path.append(str(Path(__file__).parent))
    
    success = asyncio.run(main())
    sys.exit(0 if success else 1)