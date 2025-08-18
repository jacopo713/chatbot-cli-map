"""
Concept Map Analyzer for extracting user thinking patterns and semantic metadata
Integrates with existing hybrid memory system to enhance LLM responses
"""

import asyncio
import logging
from typing import Dict, List, Optional, Tuple, Any, Set
from dataclasses import dataclass, asdict
from collections import defaultdict, Counter
import statistics
from datetime import datetime

logger = logging.getLogger(__name__)

# Data structures for pattern analysis
@dataclass
class ConceptMapData:
    """Represents a concept map with nodes and edges"""
    title: Optional[str]
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]
    
@dataclass 
class ThinkingPattern:
    """User's thinking patterns extracted from concept maps"""
    preferred_relationship_types: Dict[str, float]  # relationship_type -> frequency
    concept_granularity: float  # avg concepts per map
    connection_density: float   # edges per node ratio
    hierarchical_preference: float  # preference for hierarchical structures
    causal_preference: float    # preference for causal reasoning
    temporal_evolution: Dict[str, Any]  # how concepts evolve over time
    concept_categories: Dict[str, int]  # concept types user focuses on
    
@dataclass
class ConceptSemantics:
    """Semantic metadata for concepts and relationships"""
    concept_clusters: Dict[str, List[str]]  # concept_id -> related_concept_ids
    causal_chains: List[List[str]]  # chains of cause-effect relationships
    hierarchical_trees: Dict[str, List[str]]  # parent -> children mapping
    knowledge_domains: Set[str]  # identified knowledge domains
    relationship_strength: Dict[str, float]  # edge_id -> calculated strength
    
class ConceptMapAnalyzer:
    """
    Analyzes concept maps to extract user thinking patterns and semantic metadata
    """
    
    def __init__(self, firebase_service=None):
        self.firebase_service = firebase_service
        self._analysis_cache = {}
        self._cache_timestamp = None
        self._cache_duration = 3600  # 1 hour cache
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
        
    async def load_all_concept_maps(self, user_id: Optional[str] = None) -> List[Tuple[str, ConceptMapData]]:
        """Load all concept maps from Firebase with caching"""
        # Check cache first
        cache_key = f'concept_maps_{user_id}' if user_id else 'concept_maps_global'
        if self._is_cache_valid() and cache_key in self._analysis_cache:
            return self._analysis_cache[cache_key]
        
        concept_maps = []
        
        if not self.firebase_service:
            logger.warning("Firebase service not available for concept map loading")
            return concept_maps
            
        try:
            # Load concept maps from Firebase
            if user_id:
                firebase_maps = await self.firebase_service.get_user_concept_maps(user_id)
            else:
                # For backward compatibility, try to load from all users (if permitted)
                firebase_maps = []
                logger.warning("No user_id provided, concept maps analysis will be empty")
            
            for map_id, data in firebase_maps:
                try:
                    concept_map = ConceptMapData(
                        title=data.get("title"),
                        nodes=data.get("nodes", []),
                        edges=data.get("edges", [])
                    )
                    
                    concept_maps.append((map_id, concept_map))
                    
                except Exception as e:
                    logger.error(f"Failed to parse concept map {map_id}: {e}")
        
        except Exception as e:
            logger.error(f"Failed to load concept maps from Firebase: {e}")
        
        # Cache the results
        self._analysis_cache[cache_key] = concept_maps
        self._cache_timestamp = datetime.now()
        logger.info(f"Loaded and cached {len(concept_maps)} concept maps from Firebase")
                
        return concept_maps
    
    def _is_cache_valid(self) -> bool:
        """Check if cache is still valid"""
        if self._cache_timestamp is None:
            return False
        return (datetime.now() - self._cache_timestamp).total_seconds() < self._cache_duration
    
    def analyze_thinking_patterns(self, concept_maps: List[Tuple[str, ConceptMapData]]) -> ThinkingPattern:
        """Extract user's thinking patterns from concept maps"""
        
        if not concept_maps:
            logger.warning("No concept maps available for analysis")
            return ThinkingPattern(
                preferred_relationship_types={},
                concept_granularity=0.0,
                connection_density=0.0,
                hierarchical_preference=0.0,
                causal_preference=0.0,
                temporal_evolution={},
                concept_categories={}
            )
        
        # Analyze relationship type preferences
        relationship_counts = Counter()
        total_relationships = 0
        
        # Analyze map characteristics
        map_sizes = []
        connection_densities = []
        hierarchical_scores = []
        causal_scores = []
        concept_categories = Counter()
        
        for map_id, concept_map in concept_maps:
            num_nodes = len(concept_map.nodes)
            num_edges = len(concept_map.edges)
            
            if num_nodes > 0:
                map_sizes.append(num_nodes)
                connection_densities.append(num_edges / num_nodes if num_nodes > 0 else 0)
                
                # Analyze relationships
                hierarchical_count = 0
                causal_count = 0
                
                for edge in concept_map.edges:
                    rel_type = edge.get("relationshipType", "generic")
                    relationship_counts[rel_type] += 1
                    total_relationships += 1
                    
                    # Count hierarchical vs causal relationships
                    if rel_type in ["is_a", "part_of", "has"]:
                        hierarchical_count += 1
                    elif rel_type in ["causes", "leads_to", "solves", "creates"]:
                        causal_count += 1
                
                hierarchical_scores.append(hierarchical_count / num_edges if num_edges > 0 else 0)
                causal_scores.append(causal_count / num_edges if num_edges > 0 else 0)
                
                # Categorize concepts by keywords
                for node in concept_map.nodes:
                    label = node.get("label", "").lower()
                    category = self._categorize_concept(label)
                    concept_categories[category] += 1
        
        # Calculate normalized relationship preferences
        relationship_prefs = {}
        if total_relationships > 0:
            for rel_type, count in relationship_counts.items():
                relationship_prefs[rel_type] = count / total_relationships
        
        # Calculate statistics
        avg_granularity = statistics.mean(map_sizes) if map_sizes else 0.0
        avg_density = statistics.mean(connection_densities) if connection_densities else 0.0
        hierarchical_pref = statistics.mean(hierarchical_scores) if hierarchical_scores else 0.0
        causal_pref = statistics.mean(causal_scores) if causal_scores else 0.0
        
        thinking_pattern = ThinkingPattern(
            preferred_relationship_types=relationship_prefs,
            concept_granularity=avg_granularity,
            connection_density=avg_density,
            hierarchical_preference=hierarchical_pref,
            causal_preference=causal_pref,
            temporal_evolution=self._analyze_temporal_evolution(concept_maps),
            concept_categories=dict(concept_categories)
        )
        
        logger.info(f"Analyzed thinking patterns from {len(concept_maps)} concept maps")
        logger.info(f"Top relationship types: {dict(relationship_counts.most_common(3))}")
        logger.info(f"Avg granularity: {avg_granularity:.1f}, Density: {avg_density:.2f}")
        logger.info(f"Hierarchical preference: {hierarchical_pref:.2f}, Causal: {causal_pref:.2f}")
        
        return thinking_pattern
    
    def extract_semantic_metadata(self, concept_maps: List[Tuple[str, ConceptMapData]]) -> ConceptSemantics:
        """Extract semantic metadata from concept maps"""
        
        concept_clusters = defaultdict(set)
        causal_chains = []
        hierarchical_trees = defaultdict(list)
        knowledge_domains = set()
        relationship_strengths = {}
        
        # Build global concept graph
        all_concepts = {}  # concept_id -> concept_info
        all_relationships = []  # (from_id, to_id, rel_type, edge_id)
        
        for map_id, concept_map in concept_maps:
            # Collect all concepts
            for node in concept_map.nodes:
                concept_id = node.get("id")
                if concept_id:
                    all_concepts[concept_id] = {
                        "label": node.get("label", ""),
                        "map_id": map_id,
                        "x": node.get("x", 0),
                        "y": node.get("y", 0)
                    }
                    
                    # Identify knowledge domain
                    domain = self._identify_knowledge_domain(node.get("label", ""))
                    if domain:
                        knowledge_domains.add(domain)
            
            # Collect relationships
            for edge in concept_map.edges:
                from_id = edge.get("from")
                to_id = edge.get("to") 
                rel_type = edge.get("relationshipType", "generic")
                edge_id = edge.get("id")
                
                if from_id and to_id:
                    all_relationships.append((from_id, to_id, rel_type, edge_id))
                    
                    # Calculate relationship strength
                    strength = self.relationship_weights.get(rel_type, 0.5)
                    relationship_strengths[edge_id] = strength
        
        # Build concept clusters (concepts connected by strong relationships)
        for from_id, to_id, rel_type, edge_id in all_relationships:
            if self.relationship_weights.get(rel_type, 0.5) >= 0.7:  # Strong relationships only
                concept_clusters[from_id].add(to_id)
                concept_clusters[to_id].add(from_id)
        
        # Extract causal chains
        causal_chains = self._extract_causal_chains(all_relationships, all_concepts)
        
        # Build hierarchical trees
        for from_id, to_id, rel_type, edge_id in all_relationships:
            if rel_type in ["is_a", "part_of"]:
                hierarchical_trees[from_id].append(to_id)
        
        # Convert sets to lists for JSON serialization
        concept_clusters_dict = {k: list(v) for k, v in concept_clusters.items()}
        
        semantics = ConceptSemantics(
            concept_clusters=concept_clusters_dict,
            causal_chains=causal_chains,
            hierarchical_trees=dict(hierarchical_trees),
            knowledge_domains=knowledge_domains,
            relationship_strength=relationship_strengths
        )
        
        logger.info(f"Extracted semantic metadata:")
        logger.info(f"- {len(concept_clusters_dict)} concept clusters")
        logger.info(f"- {len(causal_chains)} causal chains")
        logger.info(f"- {len(hierarchical_trees)} hierarchical trees")
        logger.info(f"- {len(knowledge_domains)} knowledge domains: {list(knowledge_domains)[:5]}")
        
        return semantics
    
    def _categorize_concept(self, label: str) -> str:
        """Categorize concept by its label"""
        label_lower = label.lower()
        
        if any(word in label_lower for word in ["python", "javascript", "code", "api", "database", "algorithm"]):
            return "technical"
        elif any(word in label_lower for word in ["business", "strategy", "market", "customer", "revenue"]):
            return "business"
        elif any(word in label_lower for word in ["problem", "issue", "bug", "error", "fix"]):
            return "problem_solving"
        elif any(word in label_lower for word in ["learn", "study", "understand", "knowledge", "skill"]):
            return "learning"
        elif any(word in label_lower for word in ["project", "task", "goal", "plan", "objective"]):
            return "project_management"
        else:
            return "general"
    
    def _identify_knowledge_domain(self, label: str) -> Optional[str]:
        """Identify knowledge domain from concept label"""
        label_lower = label.lower()
        
        domains = {
            "programming": ["python", "javascript", "code", "api", "function", "class", "variable"],
            "machine_learning": ["ml", "ai", "model", "training", "neural", "algorithm", "data"],
            "web_development": ["web", "frontend", "backend", "react", "node", "html", "css"],
            "database": ["database", "sql", "query", "table", "data", "schema"],
            "business": ["business", "strategy", "market", "customer", "revenue", "profit"],
            "project_management": ["project", "task", "planning", "agile", "scrum", "timeline"]
        }
        
        for domain, keywords in domains.items():
            if any(keyword in label_lower for keyword in keywords):
                return domain
        
        return None
    
    def _extract_causal_chains(self, relationships: List[Tuple], concepts: Dict) -> List[List[str]]:
        """Extract chains of causal relationships"""
        causal_rels = [(f, t) for f, t, rel_type, _ in relationships if rel_type in ["causes", "leads_to", "creates"]]
        
        chains = []
        visited = set()
        
        for from_id, to_id in causal_rels:
            if from_id in visited:
                continue
                
            # Build chain starting from this node
            chain = [from_id]
            current = to_id
            
            while current and current not in chain:  # Avoid cycles
                chain.append(current)
                visited.add(current)
                
                # Find next node in chain
                next_node = None
                for f, t in causal_rels:
                    if f == current and t not in chain:
                        next_node = t
                        break
                current = next_node
            
            if len(chain) >= 2:  # Only include meaningful chains
                chains.append(chain)
        
        return chains
    
    def _analyze_temporal_evolution(self, concept_maps: List[Tuple[str, ConceptMapData]]) -> Dict[str, Any]:
        """Analyze how concepts evolve over time (placeholder for file timestamps)"""
        # For now, return basic stats about map creation
        # In future, could parse timestamps from filenames or metadata
        
        evolution = {
            "total_maps": len(concept_maps),
            "avg_concepts_per_map": statistics.mean([len(cm.nodes) for _, cm in concept_maps]) if concept_maps else 0,
            "complexity_trend": "stable"  # Placeholder
        }
        
        return evolution
    
    def generate_user_profile(self, thinking_pattern: ThinkingPattern, semantics: ConceptSemantics) -> Dict[str, Any]:
        """Generate comprehensive user profile for LLM enhancement"""
        
        profile = {
            "thinking_style": {
                "prefers_hierarchical_thinking": thinking_pattern.hierarchical_preference > 0.3,
                "prefers_causal_reasoning": thinking_pattern.causal_preference > 0.3,
                "concept_granularity": "detailed" if thinking_pattern.concept_granularity > 10 else "high_level",
                "connection_style": "highly_connected" if thinking_pattern.connection_density > 1.5 else "sparse"
            },
            "knowledge_domains": list(semantics.knowledge_domains),
            "preferred_relationships": thinking_pattern.preferred_relationship_types,
            "concept_categories": thinking_pattern.concept_categories,
            "reasoning_patterns": {
                "uses_causal_chains": len(semantics.causal_chains) > 0,
                "builds_hierarchies": len(semantics.hierarchical_trees) > 0,
                "creates_concept_clusters": len(semantics.concept_clusters) > 5
            },
            "metadata_for_enhancement": {
                "relationship_weights": {k: v for k, v in self.relationship_weights.items() 
                                       if k in thinking_pattern.preferred_relationship_types},
                "domain_expertise": list(semantics.knowledge_domains),
                "thinking_complexity": thinking_pattern.concept_granularity * thinking_pattern.connection_density
            }
        }
        
        return profile

# Global analyzer instance
_concept_map_analyzer: Optional[ConceptMapAnalyzer] = None

def get_concept_map_analyzer(firebase_service=None) -> ConceptMapAnalyzer:
    """Get global concept map analyzer instance"""
    global _concept_map_analyzer
    if _concept_map_analyzer is None or (_concept_map_analyzer.firebase_service is None and firebase_service is not None):
        _concept_map_analyzer = ConceptMapAnalyzer(firebase_service=firebase_service)
    return _concept_map_analyzer

async def analyze_user_concept_maps(user_id: Optional[str] = None, firebase_service=None) -> Tuple[ThinkingPattern, ConceptSemantics, Dict[str, Any]]:
    """Analyze all user concept maps and return patterns, semantics, and profile"""
    analyzer = get_concept_map_analyzer(firebase_service=firebase_service)
    
    # Load all concept maps
    concept_maps = await analyzer.load_all_concept_maps(user_id=user_id)
    
    if not concept_maps:
        logger.warning("No concept maps found for analysis")
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
    
    logger.info("Successfully analyzed user concept maps")
    return thinking_pattern, semantics, user_profile