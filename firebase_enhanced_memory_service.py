"""
Firebase-Enhanced Memory Service
Extends the enhanced memory service to work with Firebase users and concept maps
"""

import os
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass

from enhanced_memory_service import EnrichedContext, ConceptMapEnhancedMemoryService
from firebase_concept_map_analyzer import analyze_user_concept_maps_firebase
from hybrid_memory_service import get_hybrid_memory_service

logger = logging.getLogger(__name__)

class FirebaseEnhancedMemoryService(ConceptMapEnhancedMemoryService):
    """
    Enhanced memory service that works with Firebase users and their concept maps
    """
    
    def __init__(self):
        super().__init__()
        self.user_profiles_cache = {}  # user_id -> (profile, timestamp)
        self.cache_duration_hours = 6
        
    async def initialize(self):
        """Initialize the Firebase enhanced memory service"""
        # Get the existing hybrid memory service
        self.base_memory_service = get_hybrid_memory_service()
        
        if not self.base_memory_service:
            logger.warning("Base memory service not available")
            return False
            
        logger.info("Firebase enhanced memory service initialized successfully")
        return True
    
    async def _update_user_profile_firebase(self, user_id: str):
        """Update user profile by analyzing Firebase concept maps"""
        try:
            logger.info(f"Analyzing Firebase concept maps for user {user_id}...")
            
            # Analyze concept maps from Firebase
            thinking_pattern, semantics, user_profile = await analyze_user_concept_maps_firebase(user_id)
            
            # Cache the results
            self.user_profiles_cache[user_id] = {
                'thinking_pattern': thinking_pattern,
                'concept_semantics': semantics,
                'user_profile': user_profile,
                'cache_time': datetime.now()
            }
            
            logger.info(f"User profile updated for {user_id}")
            logger.info(f"Knowledge domains: {user_profile.get('knowledge_domains', [])}")
            logger.info(f"Thinking style: {user_profile.get('thinking_style', {})}")
            
        except Exception as e:
            logger.error(f"Failed to update user profile for {user_id}: {e}")
            # Set empty profile to avoid repeated failures
            self.user_profiles_cache[user_id] = {
                'thinking_pattern': None,
                'concept_semantics': None,
                'user_profile': {},
                'cache_time': datetime.now()
            }
    
    async def _ensure_fresh_user_profile(self, user_id: str):
        """Ensure user profile is fresh (re-analyze if cache is old)"""
        cached_data = self.user_profiles_cache.get(user_id)
        
        if (not cached_data or 
            (datetime.now() - cached_data['cache_time']).total_seconds() > self.cache_duration_hours * 3600):
            await self._update_user_profile_firebase(user_id)
    
    async def get_enhanced_conversation_context_for_user(
        self, 
        user_id: str,
        current_message: str, 
        conversation_id: str, 
        context_limit: int = 3
    ) -> EnrichedContext:
        """
        Get enhanced conversation context for a specific Firebase user
        """
        if not self.base_memory_service:
            return EnrichedContext(
                original_context="",
                concept_map_insights=[],
                thinking_style_hints=[],
                related_concepts=[],
                domain_context=[],
                confidence_score=0.0
            )
        
        # Ensure user profile is fresh
        await self._ensure_fresh_user_profile(user_id)
        
        # Get user-specific cached data
        cached_data = self.user_profiles_cache.get(user_id, {})
        user_thinking_pattern = cached_data.get('thinking_pattern')
        user_concept_semantics = cached_data.get('concept_semantics')
        user_profile = cached_data.get('user_profile', {})
        
        # Get original context from base memory service
        original_context = await self.base_memory_service.get_conversation_context(
            current_message, conversation_id, context_limit
        )
        
        # Enhance with user-specific concept map insights
        concept_insights = self._extract_user_concept_insights(current_message, user_concept_semantics)
        thinking_hints = self._generate_user_thinking_style_hints(current_message, user_thinking_pattern, user_profile)
        related_concepts = self._find_user_related_concepts(current_message, user_concept_semantics)
        domain_context = self._get_user_domain_context(current_message, user_profile)
        
        # Calculate confidence score based on available user data
        confidence = self._calculate_user_confidence_score(user_profile, user_thinking_pattern, user_concept_semantics)
        
        enhanced_context = EnrichedContext(
            original_context=original_context,
            concept_map_insights=concept_insights,
            thinking_style_hints=thinking_hints,
            related_concepts=related_concepts,
            domain_context=domain_context,
            confidence_score=confidence
        )
        
        logger.info(f"Enhanced context generated for user {user_id} with confidence: {confidence:.2f}")
        return enhanced_context
    
    def _extract_user_concept_insights(self, message: str, user_concept_semantics) -> List[str]:
        """Extract insights from user's concept maps relevant to the message"""
        insights = []
        
        if not user_concept_semantics:
            return insights
        
        message_lower = message.lower()
        
        # Check for causal chain insights from user's maps
        for chain in user_concept_semantics.causal_chains:
            if len(chain) >= 2:
                # Use concept IDs as labels (simplified for now)
                chain_labels = [self._clean_concept_label(concept_id) for concept_id in chain]
                if any(label and any(word in message_lower for word in label.lower().split()) 
                      for label in chain_labels):
                    clean_chain = [label for label in chain_labels if label]
                    if len(clean_chain) >= 2:
                        insights.append(f"🔗 Dalle tue mappe: {' → '.join(clean_chain[:3])}")
        
        # Check for hierarchical relationships from user's maps
        for parent, children in user_concept_semantics.hierarchical_trees.items():
            parent_label = self._clean_concept_label(parent)
            if parent_label and any(word in message_lower for word in parent_label.lower().split()):
                child_labels = [self._clean_concept_label(child) for child in children[:3]]
                child_labels = [label for label in child_labels if label]
                if child_labels:
                    insights.append(f"🏗️ Concetti correlati dalle tue mappe: {', '.join(child_labels)}")
        
        return insights[:3]  # Limit to 3 most relevant insights
    
    def _generate_user_thinking_style_hints(self, message: str, user_thinking_pattern, user_profile: Dict) -> List[str]:
        """Generate hints based on user's specific thinking style"""
        hints = []
        
        if not user_thinking_pattern or not user_profile:
            return hints
        
        thinking_style = user_profile.get('thinking_style', {})
        
        # User-specific hierarchical thinking preference
        if thinking_style.get('prefers_hierarchical_thinking'):
            hints.append("💡 Basandomi sul tuo stile: preferisci strutture gerarchiche e categorizzazioni")
        
        # User-specific causal reasoning preference  
        if thinking_style.get('prefers_causal_reasoning'):
            hints.append("⚡ Dal tuo modo di ragionare: spesso pensi per cause ed effetti")
        
        # User-specific granularity preference
        granularity = thinking_style.get('concept_granularity', 'unknown')
        if granularity == 'detailed':
            hints.append("🔬 Il tuo approccio: preferisci analisi dettagliate e granulari")
        elif granularity == 'high_level':
            hints.append("🔭 Il tuo stile: preferisci visioni high-level e sintesi")
        
        # User-specific connection style
        connection_style = thinking_style.get('connection_style', 'unknown')
        if connection_style == 'highly_connected':
            hints.append("🕸️ Dalle tue mappe: crei molte connessioni tra concetti")
        
        # User-specific top relationship types
        if user_thinking_pattern.preferred_relationship_types:
            top_rel = max(user_thinking_pattern.preferred_relationship_types.items(), 
                         key=lambda x: x[1], default=None)
            if top_rel:
                rel_type, _ = top_rel
                rel_hint = {
                    'causes': 'relazioni causali',
                    'is_a': 'classificazioni gerarchiche', 
                    'solves': 'soluzioni ai problemi',
                    'uses': 'utilizzo di strumenti',
                    'leads_to': 'sequenze logiche'
                }.get(rel_type, f'relazioni {rel_type}')
                hints.append(f"🎯 Il tuo pattern preferito: {rel_hint}")
        
        return hints
    
    def _find_user_related_concepts(self, message: str, user_concept_semantics) -> List[str]:
        """Find concepts related to the message from user's concept maps"""
        related = []
        
        if not user_concept_semantics:
            return related
        
        message_lower = message.lower()
        
        # Look for concept clusters from user's maps
        for concept_id, cluster in user_concept_semantics.concept_clusters.items():
            concept_label = self._clean_concept_label(concept_id)
            if concept_label and any(word in message_lower for word in concept_label.lower().split()):
                # Add related concepts from user's cluster
                for related_id in cluster[:3]:  # Limit to 3
                    related_label = self._clean_concept_label(related_id)
                    if related_label and related_label not in related:
                        related.append(related_label)
        
        return related[:5]  # Limit to 5 related concepts
    
    def _get_user_domain_context(self, message: str, user_profile: Dict) -> List[str]:
        """Get domain-specific context based on user's expertise"""
        domain_context = []
        
        if not user_profile:
            return domain_context
        
        user_domains = user_profile.get('knowledge_domains', [])
        message_lower = message.lower()
        
        domain_keywords = {
            'programming': ['code', 'function', 'api', 'bug', 'debug', 'python', 'javascript', 'software'],
            'machine_learning': ['model', 'training', 'data', 'algorithm', 'ai', 'ml', 'neural', 'learning'],
            'web_development': ['web', 'frontend', 'backend', 'react', 'node', 'html', 'css', 'website'],
            'business': ['strategy', 'market', 'customer', 'revenue', 'business', 'company'],
            'project_management': ['project', 'task', 'planning', 'agile', 'timeline', 'management']
        }
        
        for domain in user_domains:
            if domain in domain_keywords:
                keywords = domain_keywords[domain]
                if any(keyword in message_lower for keyword in keywords):
                    domain_context.append(f"🎯 Dalle tue competenze in {domain.replace('_', ' ')}")
        
        return domain_context
    
    def _calculate_user_confidence_score(self, user_profile: Dict, user_thinking_pattern, user_concept_semantics) -> float:
        """Calculate confidence score based on user-specific data quality"""
        score = 0.0
        
        # Base score from having user profile
        if user_profile:
            score += 0.4
        
        # Score from user thinking pattern quality
        if user_thinking_pattern:
            if user_thinking_pattern.concept_granularity > 0:
                score += 0.2
            if user_thinking_pattern.preferred_relationship_types:
                score += 0.2
        
        # Score from user semantic data
        if user_concept_semantics:
            if user_concept_semantics.concept_clusters:
                score += 0.1
            if user_concept_semantics.causal_chains:
                score += 0.1
        
        return min(1.0, score)
    
    def _clean_concept_label(self, concept_id: str) -> Optional[str]:
        """Clean concept ID to make it more readable"""
        if not concept_id:
            return None
            
        # Remove common prefixes and clean up
        label = concept_id.replace('n_', '').replace('node_', '')
        label = label.replace('_', ' ').strip()
        
        # Return None if too short or just numbers
        if len(label) < 3 or label.isdigit():
            return None
            
        return label.title()
    
    def format_enhanced_context_for_user(self, enhanced_context: EnrichedContext, user_id: str) -> str:
        """Format enhanced context specifically for the user"""
        if not enhanced_context.original_context and not any([
            enhanced_context.concept_map_insights,
            enhanced_context.thinking_style_hints,
            enhanced_context.related_concepts,
            enhanced_context.domain_context
        ]):
            return ""
        
        context_parts = []
        
        # Original memory context
        if enhanced_context.original_context:
            context_parts.append(enhanced_context.original_context)
        
        # User-specific concept map insights
        if enhanced_context.concept_map_insights:
            context_parts.append("## 🧠 Insight dalle tue mappe concettuali:")
            for insight in enhanced_context.concept_map_insights:
                context_parts.append(f"- {insight}")
        
        # User-specific thinking style hints
        if enhanced_context.thinking_style_hints:
            context_parts.append("## 💭 Il tuo stile di pensiero:")
            for hint in enhanced_context.thinking_style_hints:
                context_parts.append(f"- {hint}")
        
        # User-specific related concepts
        if enhanced_context.related_concepts:
            context_parts.append("## 🔗 Concetti dalle tue mappe:")
            context_parts.append(f"- {', '.join(enhanced_context.related_concepts)}")
        
        # User-specific domain context
        if enhanced_context.domain_context:
            context_parts.append("## 🎯 Le tue competenze:")
            for context in enhanced_context.domain_context:
                context_parts.append(f"- {context}")
        
        # Confidence indicator with user context
        if enhanced_context.confidence_score > 0:
            confidence_emoji = "🔥" if enhanced_context.confidence_score > 0.7 else "⭐" if enhanced_context.confidence_score > 0.4 else "💡"
            context_parts.append(f"\n{confidence_emoji} *Personalizzazione basata sulle tue {len(self.user_profiles_cache.get(user_id, {}).get('user_profile', {}).get('knowledge_domains', []))} aree di expertise*")
        
        return "\n".join(context_parts)

# Global Firebase enhanced memory service instance
_firebase_enhanced_memory_service: Optional[FirebaseEnhancedMemoryService] = None

async def get_firebase_enhanced_memory_service() -> Optional[FirebaseEnhancedMemoryService]:
    """Get or initialize the Firebase enhanced memory service"""
    global _firebase_enhanced_memory_service
    
    if _firebase_enhanced_memory_service is None:
        _firebase_enhanced_memory_service = FirebaseEnhancedMemoryService()
        success = await _firebase_enhanced_memory_service.initialize()
        if not success:
            logger.warning("Firebase enhanced memory service initialization failed")
            return None
    
    return _firebase_enhanced_memory_service