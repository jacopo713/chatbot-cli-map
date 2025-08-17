"""
Firebase-enabled Concept Map Analyzer
Extends the original analyzer to work with Firebase Firestore instead of local JSON files
"""

import logging
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime

from concept_map_analyzer import (
    ConceptMapData, ThinkingPattern, ConceptSemantics, ConceptMapAnalyzer
)
from firebase_service import get_firebase_service

logger = logging.getLogger(__name__)

class FirebaseConceptMapAnalyzer:
    """
    Concept Map Analyzer that works with Firebase Firestore
    """
    
    def __init__(self):
        self.firebase_service = None
        self.relationship_weights = {
            "causes": 1.0,      # Strong logical connection
            "is_a": 0.9,        # Hierarchical classification
            "part_of": 0.8,     # Compositional relationship
            "has": 0.7,         # Possession/attribute
            "needs": 0.9,       # Dependency
            "solves": 1.0,      # Problem-solution
            "uses": 0.8,        # Tool/method usage
            "leads_to": 0.9,    # Sequential/temporal
            "similar_to": 0.6,  # Analogical
            "opposite_to": 0.7, # Contrast
            "depends_on": 0.9,  # Dependency
            "creates": 0.8,     # Production
            "generic": 0.5      # Weak connection
        }
        
    async def initialize(self):
        """Initialize Firebase service"""
        self.firebase_service = await get_firebase_service()
        return self.firebase_service is not None
        
    async def load_user_concept_maps(self, user_id: str) -> List[Tuple[str, ConceptMapData]]:
        """Load all concept maps for a specific user from Firebase"""
        if not self.firebase_service:
            await self.initialize()
            
        if not self.firebase_service:
            logger.warning("Firebase service not available")
            return []
            
        try:
            firebase_maps = await self.firebase_service.get_user_concept_maps(user_id)
            concept_maps = []
            
            for firebase_map in firebase_maps:
                try:
                    concept_map = ConceptMapData(
                        title=firebase_map.get("title"),
                        nodes=firebase_map.get("nodes", []),
                        edges=firebase_map.get("edges", [])
                    )
                    
                    map_id = firebase_map.get("id", f"map_{len(concept_maps)}")
                    concept_maps.append((map_id, concept_map))
                    
                    logger.info(f"Loaded concept map: {map_id} ({len(concept_map.nodes)} nodes, {len(concept_map.edges)} edges)")
                    
                except Exception as e:
                    logger.error(f"Failed to parse concept map {firebase_map.get('id', 'unknown')}: {e}")
                    continue
                    
            logger.info(f"Loaded {len(concept_maps)} concept maps for user {user_id}")
            return concept_maps
            
        except Exception as e:
            logger.error(f"Failed to load concept maps for user {user_id}: {e}")
            return []
    
    def analyze_thinking_patterns(self, concept_maps: List[Tuple[str, ConceptMapData]]) -> ThinkingPattern:
        """Analyze thinking patterns from concept maps (same logic as original)"""
        # Use the same logic from the original analyzer
        from concept_map_analyzer import ConceptMapAnalyzer
        analyzer = ConceptMapAnalyzer()
        return analyzer.analyze_thinking_patterns(concept_maps)
    
    def extract_semantic_metadata(self, concept_maps: List[Tuple[str, ConceptMapData]]) -> ConceptSemantics:
        """Extract semantic metadata from concept maps (same logic as original)"""
        # Use the same logic from the original analyzer
        from concept_map_analyzer import ConceptMapAnalyzer
        analyzer = ConceptMapAnalyzer()
        return analyzer.extract_semantic_metadata(concept_maps)
    
    def generate_user_profile(self, thinking_pattern: ThinkingPattern, semantics: ConceptSemantics) -> Dict[str, Any]:
        """Generate user profile (same logic as original)"""
        # Use the same logic from the original analyzer
        from concept_map_analyzer import ConceptMapAnalyzer
        analyzer = ConceptMapAnalyzer()
        return analyzer.generate_user_profile(thinking_pattern, semantics)
    
    async def store_user_analysis(self, user_id: str, thinking_pattern: ThinkingPattern, 
                                 semantics: ConceptSemantics, user_profile: Dict[str, Any]) -> bool:
        """Store user analysis results in Firebase"""
        if not self.firebase_service:
            await self.initialize()
            
        if not self.firebase_service:
            return False
            
        try:
            # Convert dataclasses to dicts for Firebase storage
            from dataclasses import asdict
            
            analysis_data = {
                "thinking_pattern": asdict(thinking_pattern),
                "semantics": {
                    "concept_clusters": semantics.concept_clusters,
                    "causal_chains": semantics.causal_chains,
                    "hierarchical_trees": semantics.hierarchical_trees,
                    "knowledge_domains": list(semantics.knowledge_domains),
                    "relationship_strength": semantics.relationship_strength
                },
                "user_profile": user_profile,
                "analyzed_at": datetime.now(),
                "analyzer_version": "firebase_v1.0"
            }
            
            success = await self.firebase_service.store_user_profile(user_id, analysis_data)
            if success:
                logger.info(f"Stored analysis results for user {user_id}")
            return success
            
        except Exception as e:
            logger.error(f"Failed to store user analysis: {e}")
            return False
    
    async def get_cached_user_analysis(self, user_id: str) -> Optional[Tuple[ThinkingPattern, ConceptSemantics, Dict[str, Any]]]:
        """Get cached user analysis from Firebase"""
        if not self.firebase_service:
            await self.initialize()
            
        if not self.firebase_service:
            return None
            
        try:
            profile_data = await self.firebase_service.get_user_profile(user_id)
            if not profile_data:
                return None
                
            # Check if analysis is recent (less than 6 hours old)
            analyzed_at = profile_data.get("analyzed_at")
            if analyzed_at:
                if isinstance(analyzed_at, str):
                    analyzed_at = datetime.fromisoformat(analyzed_at)
                elif hasattr(analyzed_at, 'seconds'):  # Firestore timestamp
                    analyzed_at = datetime.fromtimestamp(analyzed_at.seconds)
                    
                age_hours = (datetime.now() - analyzed_at).total_seconds() / 3600
                if age_hours > 6:  # Cache expired
                    logger.info(f"Cached analysis for user {user_id} is {age_hours:.1f} hours old, will refresh")
                    return None
            
            # Reconstruct objects from stored data
            thinking_data = profile_data.get("thinking_pattern", {})
            thinking_pattern = ThinkingPattern(
                preferred_relationship_types=thinking_data.get("preferred_relationship_types", {}),
                concept_granularity=thinking_data.get("concept_granularity", 0.0),
                connection_density=thinking_data.get("connection_density", 0.0),
                hierarchical_preference=thinking_data.get("hierarchical_preference", 0.0),
                causal_preference=thinking_data.get("causal_preference", 0.0),
                temporal_evolution=thinking_data.get("temporal_evolution", {}),
                concept_categories=thinking_data.get("concept_categories", {})
            )
            
            semantics_data = profile_data.get("semantics", {})
            semantics = ConceptSemantics(
                concept_clusters=semantics_data.get("concept_clusters", {}),
                causal_chains=semantics_data.get("causal_chains", []),
                hierarchical_trees=semantics_data.get("hierarchical_trees", {}),
                knowledge_domains=set(semantics_data.get("knowledge_domains", [])),
                relationship_strength=semantics_data.get("relationship_strength", {})
            )
            
            user_profile = profile_data.get("user_profile", {})
            
            logger.info(f"Retrieved cached analysis for user {user_id}")
            return thinking_pattern, semantics, user_profile
            
        except Exception as e:
            logger.error(f"Failed to get cached user analysis: {e}")
            return None

# Enhanced analysis function for Firebase users
async def analyze_user_concept_maps_firebase(user_id: str) -> Tuple[ThinkingPattern, ConceptSemantics, Dict[str, Any]]:
    """
    Analyze concept maps for a specific Firebase user
    """
    analyzer = FirebaseConceptMapAnalyzer()
    
    # Try to get cached analysis first
    cached_result = await analyzer.get_cached_user_analysis(user_id)
    if cached_result:
        logger.info(f"Using cached analysis for user {user_id}")
        return cached_result
    
    # Load user's concept maps from Firebase
    concept_maps = await analyzer.load_user_concept_maps(user_id)
    
    if not concept_maps:
        logger.warning(f"No concept maps found for user {user_id}")
        # Return default empty analysis
        return ThinkingPattern(
            preferred_relationship_types={},
            concept_granularity=0.0,
            connection_density=0.0,
            hierarchical_preference=0.0,
            causal_preference=0.0,
            temporal_evolution={},
            concept_categories={}
        ), ConceptSemantics(
            concept_clusters={},
            causal_chains=[],
            hierarchical_trees={},
            knowledge_domains=set(),
            relationship_strength={}
        ), {}
    
    # Analyze patterns and semantics
    thinking_pattern = analyzer.analyze_thinking_patterns(concept_maps)
    semantics = analyzer.extract_semantic_metadata(concept_maps)
    user_profile = analyzer.generate_user_profile(thinking_pattern, semantics)
    
    # Cache the results in Firebase
    await analyzer.store_user_analysis(user_id, thinking_pattern, semantics, user_profile)
    
    logger.info(f"Completed fresh analysis for user {user_id} with {len(concept_maps)} maps")
    return thinking_pattern, semantics, user_profile

# Global Firebase analyzer instance
_firebase_analyzer: Optional[FirebaseConceptMapAnalyzer] = None

async def get_firebase_concept_map_analyzer() -> FirebaseConceptMapAnalyzer:
    """Get global Firebase concept map analyzer instance"""
    global _firebase_analyzer
    if _firebase_analyzer is None:
        _firebase_analyzer = FirebaseConceptMapAnalyzer()
        await _firebase_analyzer.initialize()
    return _firebase_analyzer