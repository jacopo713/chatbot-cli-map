"""
Enhanced Memory Service with Concept Map Integration
Extends the existing hybrid memory system with semantic metadata from concept maps
"""

import os
import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from pathlib import Path

from hybrid_memory_service import (
    HybridMemoryService, HybridMemoryConfig, HybridMemoryItem, 
    ImportanceLevel, StorageTier, get_hybrid_memory_service
)
from concept_map_analyzer import (
    analyze_user_concept_maps, ThinkingPattern, ConceptSemantics,
    get_concept_map_analyzer
)

logger = logging.getLogger(__name__)

@dataclass
class EnrichedContext:
    """Enhanced context with concept map insights"""
    original_context: str
    concept_map_insights: List[str]
    thinking_style_hints: List[str]
    related_concepts: List[str]
    domain_context: List[str]
    active_map_context: List[str]
    confidence_score: float

class ConceptMapEnhancedMemoryService:
    """
    Enhanced memory service that leverages concept maps for better context generation
    """
    
    def __init__(self, firebase_service=None):
        self.base_memory_service = None
        self.firebase_service = firebase_service
        self.user_profiles = {}  # Cache per utente
        self.thinking_patterns = {}  # Cache per utente
        self.concept_semantics_cache = {}  # Cache per utente
        self.profile_cache_times = {}  # Cache timestamps per utente
        self.cache_duration_hours = 6  # Re-analyze every 6 hours
        
    async def initialize(self):
        """Initialize the enhanced memory service"""
        # Get the existing hybrid memory service
        self.base_memory_service = get_hybrid_memory_service()
        
        if not self.base_memory_service:
            logger.warning("Base memory service not available")
            return False
            
        # Analyze concept maps to build user profile
        await self._update_user_profile()
        
        logger.info("Enhanced memory service with concept map integration initialized")
        return True
    
    async def _update_user_profile(self, user_id: Optional[str] = None):
        """Update user profile by analyzing concept maps"""
        try:
            logger.info(f"Analyzing concept maps to build user profile for user: {user_id}")
            
            # Analyze all concept maps using Firebase service
            thinking_pattern, semantics, user_profile = await analyze_user_concept_maps(
                user_id=user_id, 
                firebase_service=self.firebase_service
            )
            
            # Store in user-specific cache
            cache_key = user_id or 'default'
            self.thinking_patterns[cache_key] = thinking_pattern
            self.concept_semantics_cache[cache_key] = semantics
            self.user_profiles[cache_key] = user_profile
            self.profile_cache_times[cache_key] = datetime.now()
            
            logger.info(f"User profile updated successfully for {user_id}")
            logger.info(f"Knowledge domains: {user_profile.get('knowledge_domains', [])}")
            logger.info(f"Thinking style: {user_profile.get('thinking_style', {})}")
            
        except Exception as e:
            logger.error(f"Failed to update user profile for {user_id}: {e}")
            cache_key = user_id or 'default'
            self.user_profiles[cache_key] = {}
    
    async def _ensure_fresh_profile(self, user_id: Optional[str] = None):
        """Ensure user profile is fresh (re-analyze if cache is old)"""
        cache_key = user_id or 'default'
        logger.info(f"Checking profile freshness for user_id: {user_id} (cache_key: {cache_key})")
        
        profile_cache_time = self.profile_cache_times.get(cache_key)
        if (not profile_cache_time or 
            (datetime.now() - profile_cache_time).total_seconds() > self.cache_duration_hours * 3600):
            # Only update if we actually have concept maps to analyze
            logger.info(f"Profile cache expired or missing, reloading concept maps for user: {user_id}")
            analyzer = get_concept_map_analyzer(firebase_service=self.firebase_service)
            maps = await analyzer.load_all_concept_maps(user_id=user_id)
            logger.info(f"Loaded {len(maps)} concept maps for user {user_id}")
            if maps:  # Only analyze if maps exist
                await self._update_user_profile(user_id=user_id)
            else:
                logger.warning(f"No concept maps found for user {user_id} - skipping profile update")
        else:
            logger.info(f"Profile cache is still fresh for user {user_id}, not reloading")
    
    async def get_enhanced_conversation_context(
        self, 
        current_message: str, 
        conversation_id: str, 
        context_limit: int = 3,
        active_concept_map_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> EnrichedContext:
        """
        Get enhanced conversation context using concept map insights
        """
        if not self.base_memory_service:
            return EnrichedContext(
                original_context="",
                concept_map_insights=[],
                thinking_style_hints=[],
                related_concepts=[],
                domain_context=[],
                active_map_context=[],
                confidence_score=0.0
            )
        
        # Ensure profile is fresh
        await self._ensure_fresh_profile(user_id=user_id)
        
        # Set current user data for legacy compatibility
        cache_key = user_id or 'default'
        self.concept_semantics = self.concept_semantics_cache.get(cache_key)
        self.thinking_pattern = self.thinking_patterns.get(cache_key)
        self.user_profile = self.user_profiles.get(cache_key, {})
        
        # Get original context from base memory service
        original_context = await self.base_memory_service.get_conversation_context(
            current_message, conversation_id, context_limit
        )
        
        # Enhance with concept map insights (weighted by active map)
        concept_insights = await self._extract_concept_insights(current_message, active_concept_map_id, user_id)
        thinking_hints = self._generate_thinking_style_hints(current_message, user_id)
        related_concepts = await self._find_related_concepts(current_message, active_concept_map_id, user_id)
        domain_context = self._get_domain_context(current_message, user_id)
        
        # Add active map context if available
        active_map_context = []
        if active_concept_map_id:
            active_map_context = await self._get_active_map_context(active_concept_map_id, current_message)
        
        # Calculate confidence score based on available data and original context
        confidence = self._calculate_confidence_score(original_context)
        
        enhanced_context = EnrichedContext(
            original_context=original_context,
            concept_map_insights=concept_insights,
            thinking_style_hints=thinking_hints,
            related_concepts=related_concepts,
            domain_context=domain_context,
            active_map_context=active_map_context,
            confidence_score=confidence
        )
        
        logger.info(f"Enhanced context generated with confidence: {confidence:.2f}")
        return enhanced_context
    
    async def _extract_concept_insights(self, message: str, active_map_id: Optional[str] = None, user_id: Optional[str] = None) -> List[str]:
        """Extract insights from concept maps relevant to the message"""
        insights = []
        logger.info(f"Extracting concept insights for message: '{message[:50]}...', concept_semantics available: {bool(self.concept_semantics)}")
        
        # Get user-specific data
        cache_key = user_id or 'default'
        concept_semantics = self.concept_semantics_cache.get(cache_key)
        
        # Update legacy properties for backward compatibility
        self.concept_semantics = concept_semantics
        
        if not concept_semantics:
            logger.warning(f"No concept semantics available for insight extraction (cache_key: {cache_key})")
            return insights
        
        message_lower = message.lower()
        message_words = [w for w in message_lower.split() if len(w) > 2]
        
        # Strategy 1: Check for causal chain insights (improved)
        for chain in self.concept_semantics.causal_chains:
            if len(chain) >= 2:
                # Get chain concepts with improved label resolution
                chain_concepts = []
                chain_matches = []
                
                for concept_id in chain:
                    concept_label = await self._get_concept_label(concept_id)
                    if concept_label:
                        chain_concepts.append(concept_label)
                        # Check if concept label matches any word in message
                        label_lower = concept_label.lower()
                        if any(word in label_lower or label_lower in message_lower for word in message_words):
                            chain_matches.append(concept_label)
                
                if chain_matches and len(chain_concepts) >= 2:
                    insights.append(f"Catena causale rilevante: {' → '.join(chain_concepts)}")
        
        # Strategy 2: Check for hierarchical relationships (improved) 
        for parent, children in self.concept_semantics.hierarchical_trees.items():
            parent_label = await self._get_concept_label(parent)
            if parent_label:
                parent_lower = parent_label.lower()
                parent_matches = any(word in parent_lower or parent_lower in message_lower for word in message_words)
                
                if parent_matches:
                    child_labels = []
                    for child in children[:3]:
                        child_label = await self._get_concept_label(child)
                        if child_label:
                            child_labels.append(child_label)
                    if child_labels:
                        insights.append(f"Sotto-concetti di {parent_label}: {', '.join(child_labels)}")
        
        # Strategy 3: Direct concept map relationship insights (NEW)
        try:
            analyzer = get_concept_map_analyzer(firebase_service=self.firebase_service)
            maps = await analyzer.load_all_concept_maps(user_id=user_id)
            
            for map_id, concept_map in maps:
                map_title = concept_map.title or "Mappa senza titolo"
                
                # Check if map title is relevant
                title_lower = map_title.lower()
                title_matches = any(word in title_lower for word in message_words)
                
                if title_matches and hasattr(concept_map, 'nodes') and hasattr(concept_map, 'edges'):
                    # Find relevant nodes in this map
                    relevant_nodes = []
                    for node in concept_map.nodes:
                        label = node.get('label', '')
                        if label:
                            label_lower = label.lower()
                            if any(word in label_lower for word in message_words):
                                relevant_nodes.append(label)
                    
                    if relevant_nodes:
                        insights.append(f"Mappa '{map_title}' contiene concetti rilevanti: {', '.join(relevant_nodes[:4])}")
                        
        except Exception as e:
            logger.debug(f"Failed to extract direct map insights: {e}")
        
        # Strategy 4: Causal chain search when no active map (NEW)
        if not active_map_id and user_id:
            try:
                analyzer = get_concept_map_analyzer(firebase_service=self.firebase_service)
                maps = await analyzer.load_all_concept_maps(user_id=user_id)
                
                causal_insights = []
                for map_id, concept_map in maps:
                    # Search for causal relationships with relevant keywords
                    for edge in concept_map.edges:
                        rel_type = edge.get('relationshipType', '')
                        if rel_type in ['causes', 'leads_to', 'creates', 'results_in']:
                            from_node = next((n for n in concept_map.nodes if n.get('id') == edge.get('from')), None)
                            to_node = next((n for n in concept_map.nodes if n.get('id') == edge.get('to')), None)
                            
                            if from_node and to_node:
                                from_label = from_node.get('label', '').lower()
                                to_label = to_node.get('label', '').lower()
                                
                                # Check if message keywords match the causal relationship
                                match_found = False
                                for word in message_words:
                                    if (word in from_label or word in to_label or 
                                        from_label in message_lower or to_label in message_lower):
                                        match_found = True
                                        break
                                
                                if match_found:
                                    causal_insight = f"Collegamento causale: {from_node.get('label')} → {to_node.get('label')}"
                                    if causal_insight not in causal_insights:
                                        causal_insights.append(causal_insight)
                
                if causal_insights:
                    insights.extend(causal_insights[:3])  # Add up to 3 causal insights
                    logger.info(f"Found {len(causal_insights)} causal insights for message: {message[:30]}...")
                    
            except Exception as e:
                logger.debug(f"Failed to extract causal insights: {e}")
        
        return insights[:8]  # Increased limit to include causal insights
    
    def _generate_thinking_style_hints(self, message: str, user_id: Optional[str] = None) -> List[str]:
        """Generate hints based on user's thinking style"""
        hints = []
        
        cache_key = user_id or 'default'
        thinking_pattern = self.thinking_patterns.get(cache_key)
        
        # Update legacy property for backward compatibility
        self.thinking_pattern = thinking_pattern
        
        if not thinking_pattern:
            return hints
        
        # Hierarchical thinking preference
        if thinking_pattern.hierarchical_preference > 0.3:
            hints.append("L'utente preferisce strutture gerarchiche e categorizzazioni")
        
        # Causal reasoning preference  
        if thinking_pattern.causal_preference > 0.3:
            hints.append("L'utente ragiona spesso per cause ed effetti")
        
        # High-level vs detailed thinking
        if thinking_pattern.concept_granularity > 10:
            hints.append("L'utente preferisce analisi dettagliate e granulari")
        elif thinking_pattern.concept_granularity < 5:
            hints.append("L'utente preferisce visioni high-level e sintesi")
        
        # Connection style
        if thinking_pattern.connection_density > 1.5:
            hints.append("L'utente crea molte connessioni tra concetti")
        
        # Preferred relationship types
        top_relationships = sorted(
            thinking_pattern.preferred_relationship_types.items(),
            key=lambda x: x[1], reverse=True
        )[:2]
        
        if top_relationships:
            rel_names = []
            for rel_type, _ in top_relationships:
                if rel_type == "causes":
                    rel_names.append("relazioni causali")
                elif rel_type == "is_a":
                    rel_names.append("classificazioni")
                elif rel_type == "solves":
                    rel_names.append("soluzioni ai problemi")
                elif rel_type == "uses":
                    rel_names.append("utilizzo di strumenti")
            
            if rel_names:
                hints.append(f"L'utente usa spesso: {', '.join(rel_names)}")
        
        return hints
    
    async def _find_related_concepts(self, message: str, active_map_id: Optional[str] = None, user_id: Optional[str] = None) -> List[str]:
        """Find concepts related to the message from concept maps"""
        related = []
        
        cache_key = user_id or 'default'
        concept_semantics = self.concept_semantics_cache.get(cache_key)
        
        if not concept_semantics:
            return related
        
        message_lower = message.lower()
        message_words = [w for w in message_lower.split() if len(w) > 2]  # Skip short words
        
        # Strategy 1: Look for concept clusters (existing logic, now with fixed labels)
        for concept_id, cluster in concept_semantics.concept_clusters.items():
            concept_label = await self._get_concept_label(concept_id)
            if concept_label and concept_label.lower() in message_lower:
                # Add related concepts from cluster
                for related_id in cluster[:3]:  # Limit to 3
                    related_label = await self._get_concept_label(related_id)
                    if related_label and related_label not in related:
                        related.append(related_label)
        
        # Strategy 2: Direct keyword matching across all concept maps (NEW)
        try:
            analyzer = get_concept_map_analyzer(firebase_service=self.firebase_service)
            maps = await analyzer.load_all_concept_maps(user_id=user_id)
            
            # Collect all concept labels and their relationships
            concept_matches = []
            
            for map_id, concept_map in maps:
                if hasattr(concept_map, 'nodes'):
                    for node in concept_map.nodes:
                        label = node.get('label', '').lower()
                        if label:
                            # Check if any message words appear in the concept label
                            for word in message_words:
                                if word in label or label in message_lower:
                                    concept_matches.append(node.get('label', ''))
                                    break
            
            # Add unique concept matches to related concepts
            for match in concept_matches:
                if match not in related:
                    related.append(match)
                    
        except Exception as e:
            logger.debug(f"Failed to perform keyword matching: {e}")
        
        return related[:8]  # Increased limit to capture more relevant concepts
    
    def _get_domain_context(self, message: str, user_id: Optional[str] = None) -> List[str]:
        """Get domain-specific context based on message"""
        domain_context = []
        
        cache_key = user_id or 'default'
        user_profile = self.user_profiles.get(cache_key, {})
        
        # Update legacy property for backward compatibility
        self.user_profile = user_profile
        
        if not user_profile:
            return domain_context
        
        knowledge_domains = user_profile.get('knowledge_domains', [])
        message_lower = message.lower()
        
        # Check if message relates to user's known domains
        domain_keywords = {
            'programming': ['code', 'function', 'api', 'bug', 'debug', 'python', 'javascript'],
            'machine_learning': ['model', 'training', 'data', 'algorithm', 'ai', 'ml'],
            'web_development': ['web', 'frontend', 'backend', 'react', 'node', 'html'],
            'business': ['strategy', 'market', 'customer', 'revenue', 'business'],
            'project_management': ['project', 'task', 'planning', 'agile', 'timeline']
        }
        
        for domain in knowledge_domains:
            if domain in domain_keywords:
                keywords = domain_keywords[domain]
                if any(keyword in message_lower for keyword in keywords):
                    domain_context.append(f"L'utente ha esperienza nel dominio: {domain}")
        
        return domain_context
    
    async def _get_active_map_context(self, active_map_id: str, message: str) -> List[str]:
        """Get high-priority context from the currently active concept map"""
        active_context = []
        
        try:
            # Load the specific active concept map from Firebase
            if not self.firebase_service:
                logger.warning("Firebase service not available for active map context")
                return active_context
                
            # For now, try to find the map among all loaded maps
            # In a real implementation, you'd want a specific Firebase method to get a single map
            analyzer = get_concept_map_analyzer(firebase_service=self.firebase_service)
            maps = await analyzer.load_all_concept_maps()
            
            active_map_data = None
            for map_id, concept_map in maps:
                if map_id == active_map_id:
                    active_map_data = {
                        "title": concept_map.title,
                        "nodes": concept_map.nodes,
                        "edges": concept_map.edges
                    }
                    break
            
            if active_map_data:
                    
                message_lower = message.lower()
                
                # Extract full context from active map with high priority
                nodes = active_map_data.get("nodes", [])
                edges = active_map_data.get("edges", [])
                
                # Find relevant nodes in active map (higher weight)
                relevant_nodes = []
                for node in nodes:
                    node_label = node.get("label", "").lower()
                    if any(word in node_label for word in message_lower.split() if len(word) > 2):
                        relevant_nodes.append(node.get("label", ""))
                
                if relevant_nodes:
                    active_context.append(f"🎯 MAPPA ATTIVA - Concetti rilevanti: {', '.join(relevant_nodes[:5])}")
                
                # Extract key relationships from active map
                relevant_relationships = []
                for edge in edges:
                    from_node = next((n.get("label") for n in nodes if n.get("id") == edge.get("from")), "")
                    to_node = next((n.get("label") for n in nodes if n.get("id") == edge.get("to")), "")
                    rel_type = edge.get("relationshipType", "generic")
                    
                    if from_node and to_node:
                        from_lower, to_lower = from_node.lower(), to_node.lower()
                        if any(word in from_lower or word in to_lower for word in message_lower.split() if len(word) > 2):
                            relevant_relationships.append(f"{from_node} → {to_node} ({rel_type})")
                
                if relevant_relationships:
                    active_context.append(f"🎯 MAPPA ATTIVA - Relazioni chiave: {'; '.join(relevant_relationships[:3])}")
                    
                # Add map title for context
                map_title = active_map_data.get("title")
                if map_title:
                    active_context.insert(0, f"🎯 CONTESTO MAPPA ATTIVA: {map_title}")
                    
        except Exception as e:
            logger.warning(f"Failed to load active concept map {active_map_id}: {e}")
        
        return active_context[:4]  # Limit to 4 most important active context items
    
    async def _get_concept_label(self, concept_id: str) -> Optional[str]:
        """Get concept label from concept ID by searching through loaded concept maps"""
        if not concept_id:
            return None
            
        try:
            # Get the concept map analyzer to access loaded maps
            analyzer = get_concept_map_analyzer(firebase_service=self.firebase_service)
            maps = await analyzer.load_all_concept_maps()  # Use cached maps
            
            # Search for the concept_id in all maps
            for map_id, concept_map in maps:
                if hasattr(concept_map, 'nodes'):
                    for node in concept_map.nodes:
                        if node.get('id') == concept_id:
                            label = node.get('label', '')
                            if label:
                                return label
                                
        except Exception as e:
            logger.debug(f"Failed to get concept label for {concept_id}: {e}")
            
        # Fallback: clean up the concept_id
        return concept_id.replace('_', ' ') if concept_id else None
    
    def _calculate_confidence_score(self, original_context: str = "") -> float:
        """Calculate confidence score based on available data quality and base memory"""
        score = 0.0
        
        # CRITICAL: Base score from having memory content - this should always work!
        if original_context and original_context.strip():
            score += 0.6  # High base confidence when we have memory data
        
        # Additional score from having any profile data
        if self.user_profile:
            score += 0.1
        
        # Score from thinking pattern quality
        if self.thinking_pattern:
            if self.thinking_pattern.concept_granularity > 0:
                score += 0.1
            if self.thinking_pattern.preferred_relationship_types:
                score += 0.1
        
        # Score from semantic data
        if self.concept_semantics:
            if self.concept_semantics.concept_clusters:
                score += 0.05
            if self.concept_semantics.causal_chains:
                score += 0.05
        
        return min(1.0, score)
    
    def format_enhanced_context(self, enhanced_context: EnrichedContext) -> str:
        """Format enhanced context for LLM consumption"""
        if not enhanced_context.original_context and not any([
            enhanced_context.concept_map_insights,
            enhanced_context.thinking_style_hints,
            enhanced_context.related_concepts,
            enhanced_context.domain_context,
            enhanced_context.active_map_context
        ]):
            return ""
        
        context_parts = []
        
        # Active map context (highest priority)
        if enhanced_context.active_map_context:
            context_parts.append("## 🎯 CONTESTO MAPPA ATTIVA (PRIORITÀ ALTA):")
            for context in enhanced_context.active_map_context:
                context_parts.append(f"- {context}")
        
        # Original memory context
        if enhanced_context.original_context:
            context_parts.append(enhanced_context.original_context)
        
        # Concept map insights
        if enhanced_context.concept_map_insights:
            context_parts.append("## 🧠 Insight dalle mappe concettuali:")
            for insight in enhanced_context.concept_map_insights:
                context_parts.append(f"- {insight}")
        
        # Thinking style hints
        if enhanced_context.thinking_style_hints:
            context_parts.append("## 💭 Stile di pensiero dell'utente:")
            for hint in enhanced_context.thinking_style_hints:
                context_parts.append(f"- {hint}")
        
        # Related concepts
        if enhanced_context.related_concepts:
            context_parts.append("## 🔗 Concetti correlati:")
            context_parts.append(f"- {', '.join(enhanced_context.related_concepts)}")
        
        # Domain context
        if enhanced_context.domain_context:
            context_parts.append("## 🎯 Contesto di dominio:")
            for context in enhanced_context.domain_context:
                context_parts.append(f"- {context}")
        
        # Confidence indicator
        if enhanced_context.confidence_score > 0:
            confidence_emoji = "🔥" if enhanced_context.confidence_score > 0.7 else "⭐" if enhanced_context.confidence_score > 0.4 else "💡"
            context_parts.append(f"\n{confidence_emoji} *Confidenza insights: {enhanced_context.confidence_score:.1f}*")
        
        return "\n".join(context_parts)
    
    # Delegate other methods to base service
    async def store_conversation_turn(self, user_message: str, ai_response: str, conversation_id: str, additional_metadata: Dict[str, Any] = None):
        """Store conversation turn using base service"""
        if self.base_memory_service:
            return await self.base_memory_service.store_conversation_turn(
                user_message, ai_response, conversation_id, additional_metadata
            )
        return False
    
    async def retrieve_memories(self, query: str, conversation_id: str = None, limit: int = 5, include_recent: bool = True):
        """Retrieve memories using base service"""
        if self.base_memory_service:
            return await self.base_memory_service.retrieve_memories(
                query, conversation_id, limit, include_recent
            )
        return []
    
    def get_stats(self) -> Dict[str, Any]:
        """Get combined stats from base service and enhancements"""
        base_stats = self.base_memory_service.get_stats() if self.base_memory_service else {}
        
        enhancement_stats = {
            "concept_map_integration": True,
            "user_profile_available": bool(self.user_profile),
            "thinking_pattern_analyzed": bool(self.thinking_pattern),
            "concept_semantics_available": bool(self.concept_semantics),
            "profile_cache_age_hours": (
                (datetime.now() - self.profile_cache_time).total_seconds() / 3600 
                if self.profile_cache_time else None
            )
        }
        
        return {**base_stats, **enhancement_stats}

# Global enhanced memory service instance
_enhanced_memory_service: Optional[ConceptMapEnhancedMemoryService] = None

async def get_enhanced_memory_service(firebase_service=None) -> Optional[ConceptMapEnhancedMemoryService]:
    """Get or initialize the enhanced memory service"""
    global _enhanced_memory_service
    
    if _enhanced_memory_service is None or (_enhanced_memory_service.firebase_service is None and firebase_service is not None):
        _enhanced_memory_service = ConceptMapEnhancedMemoryService(firebase_service=firebase_service)
        success = await _enhanced_memory_service.initialize()
        if not success:
            logger.warning("Enhanced memory service initialization failed")
            return None
    
    return _enhanced_memory_service