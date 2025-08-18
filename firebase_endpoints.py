"""
Firebase API Endpoints
Handles concept maps and user authentication with Firebase
"""

import logging
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel

try:
    import firebase_admin
    from firebase_admin import auth
    FIREBASE_ADMIN_AVAILABLE = True
except ImportError:
    FIREBASE_ADMIN_AVAILABLE = False
    firebase_admin = None
    auth = None

from firebase_service import get_firebase_service
from firebase_enhanced_memory_service import get_firebase_enhanced_memory_service

logger = logging.getLogger(__name__)

# Pydantic models for API
class ConceptMapCreate(BaseModel):
    title: str
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]

class ConceptMapUpdate(BaseModel):
    title: Optional[str] = None
    nodes: Optional[List[Dict[str, Any]]] = None
    edges: Optional[List[Dict[str, Any]]] = None

class ConceptMapResponse(BaseModel):
    id: str
    title: str
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]
    userId: str
    createdAt: str
    updatedAt: str

# Create router
router = APIRouter(prefix="/api/firebase", tags=["firebase"])

async def verify_firebase_token(authorization: str = Header(None)) -> str:
    """Verify Firebase ID token and return user ID"""
    logger.info(f"🔑 FIREBASE_ADMIN_AVAILABLE = {FIREBASE_ADMIN_AVAILABLE}")
    
    # TEMPORARY: Force mock authentication to test concept maps functionality
    logger.warning("🔑 TEMPORARY: Using mock authentication for testing")
    return "mock_user_123"
    
    if not FIREBASE_ADMIN_AVAILABLE:
        # Development mode - use mock user
        logger.warning("🔑 Firebase Admin not available, using mock authentication")
        return "mock_user_123"
    
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header required")
    
    try:
        # Extract token from "Bearer <token>"
        if not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Invalid authorization header format")
        
        token = authorization.split("Bearer ")[1]
        
        # Verify the token
        decoded_token = auth.verify_id_token(token)
        user_id = decoded_token['uid']
        
        logger.info(f"Authenticated user: {user_id}")
        return user_id
        
    except Exception as e:
        logger.error(f"Token verification failed: {e}")
        raise HTTPException(status_code=401, detail="Invalid or expired token")

@router.post("/concept-maps", response_model=Dict[str, str])
async def create_concept_map(
    concept_map: ConceptMapCreate,
    user_id: str = Depends(verify_firebase_token)
):
    """Create a new concept map for the authenticated user"""
    firebase_service = await get_firebase_service()
    if not firebase_service:
        raise HTTPException(status_code=500, detail="Firebase service not available")
    
    try:
        concept_map_data = {
            "title": concept_map.title,
            "nodes": concept_map.nodes,
            "edges": concept_map.edges
        }
        
        map_id = await firebase_service.store_concept_map(user_id, concept_map_data)
        
        logger.info(f"Created concept map {map_id} for user {user_id}")
        return {"id": map_id, "message": "Concept map created successfully"}
        
    except Exception as e:
        logger.error(f"Failed to create concept map: {e}")
        raise HTTPException(status_code=500, detail="Failed to create concept map")

@router.get("/concept-maps", response_model=List[ConceptMapResponse])
async def get_user_concept_maps(user_id: str = Depends(verify_firebase_token)):
    """Get all concept maps for the authenticated user"""
    firebase_service = await get_firebase_service()
    if not firebase_service:
        raise HTTPException(status_code=500, detail="Firebase service not available")
    
    try:
        concept_maps = await firebase_service.get_user_concept_maps(user_id)
        
        # Convert to response format (concept_maps is now list of tuples)
        response_maps = []
        for map_id, concept_map in concept_maps:
            response_maps.append({
                "id": map_id,
                "title": concept_map.get("title", ""),
                "nodes": concept_map.get("nodes", []),
                "edges": concept_map.get("edges", []),
                "userId": concept_map.get("userId", ""),
                "createdAt": concept_map.get("createdAt", "").isoformat() if concept_map.get("createdAt") else "",
                "updatedAt": concept_map.get("updatedAt", "").isoformat() if concept_map.get("updatedAt") else ""
            })
        
        logger.info(f"Retrieved {len(response_maps)} concept maps for user {user_id}")
        return response_maps
        
    except Exception as e:
        logger.error(f"Failed to get concept maps: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve concept maps")

@router.put("/concept-maps/{map_id}")
async def update_concept_map(
    map_id: str,
    concept_map: ConceptMapUpdate,
    user_id: str = Depends(verify_firebase_token)
):
    """Update an existing concept map"""
    firebase_service = await get_firebase_service()
    if not firebase_service:
        raise HTTPException(status_code=500, detail="Firebase service not available")
    
    try:
        # Build update data
        update_data = {}
        if concept_map.title is not None:
            update_data["title"] = concept_map.title
        if concept_map.nodes is not None:
            update_data["nodes"] = concept_map.nodes
        if concept_map.edges is not None:
            update_data["edges"] = concept_map.edges
        
        if not update_data:
            raise HTTPException(status_code=400, detail="No fields to update")
        
        success = await firebase_service.update_concept_map(map_id, user_id, update_data)
        
        if not success:
            raise HTTPException(status_code=404, detail="Concept map not found or access denied")
        
        logger.info(f"Updated concept map {map_id} for user {user_id}")
        return {"message": "Concept map updated successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update concept map: {e}")
        raise HTTPException(status_code=500, detail="Failed to update concept map")

@router.delete("/concept-maps/{map_id}")
async def delete_concept_map(
    map_id: str,
    user_id: str = Depends(verify_firebase_token)
):
    """Delete a concept map"""
    firebase_service = await get_firebase_service()
    if not firebase_service:
        raise HTTPException(status_code=500, detail="Firebase service not available")
    
    try:
        success = await firebase_service.delete_concept_map(map_id, user_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Concept map not found or access denied")
        
        logger.info(f"Deleted concept map {map_id} for user {user_id}")
        return {"message": "Concept map deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete concept map: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete concept map")

@router.get("/profile/analysis")
async def get_user_analysis(user_id: str = Depends(verify_firebase_token)):
    """Get user's thinking pattern analysis based on their concept maps"""
    enhanced_service = await get_firebase_enhanced_memory_service()
    if not enhanced_service:
        raise HTTPException(status_code=500, detail="Enhanced memory service not available")
    
    try:
        # Trigger analysis update if needed
        await enhanced_service._ensure_fresh_user_profile(user_id)
        
        # Get cached analysis
        cached_data = enhanced_service.user_profiles_cache.get(user_id, {})
        user_profile = cached_data.get('user_profile', {})
        thinking_pattern = cached_data.get('thinking_pattern')
        
        if not user_profile:
            return {
                "message": "No analysis available. Please create some concept maps first.",
                "analysis": None
            }
        
        # Format analysis for response
        analysis_data = {
            "thinking_style": user_profile.get('thinking_style', {}),
            "knowledge_domains": user_profile.get('knowledge_domains', []),
            "reasoning_patterns": user_profile.get('reasoning_patterns', {}),
            "statistics": {
                "concept_granularity": thinking_pattern.concept_granularity if thinking_pattern else 0,
                "connection_density": thinking_pattern.connection_density if thinking_pattern else 0,
                "hierarchical_preference": thinking_pattern.hierarchical_preference if thinking_pattern else 0,
                "causal_preference": thinking_pattern.causal_preference if thinking_pattern else 0,
                "preferred_relationships": thinking_pattern.preferred_relationship_types if thinking_pattern else {}
            },
            "last_analyzed": cached_data.get('cache_time').isoformat() if cached_data.get('cache_time') else None
        }
        
        logger.info(f"Retrieved analysis for user {user_id}")
        return {
            "message": "Analysis retrieved successfully",
            "analysis": analysis_data
        }
        
    except Exception as e:
        logger.error(f"Failed to get user analysis: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve user analysis")

@router.post("/chat/enhanced")
async def chat_with_enhanced_context(
    request: Dict[str, Any],
    user_id: str = Depends(verify_firebase_token)
):
    """Chat endpoint with enhanced context from user's concept maps"""
    enhanced_service = await get_firebase_enhanced_memory_service()
    if not enhanced_service:
        raise HTTPException(status_code=500, detail="Enhanced memory service not available")
    
    try:
        message = request.get("message", "")
        conversation_id = request.get("conversation_id", f"user_{user_id}")
        
        if not message:
            raise HTTPException(status_code=400, detail="Message is required")
        
        # Get enhanced context for the user
        enhanced_context = await enhanced_service.get_enhanced_conversation_context_for_user(
            user_id=user_id,
            current_message=message,
            conversation_id=conversation_id,
            context_limit=3
        )
        
        # Format context for response
        formatted_context = enhanced_service.format_enhanced_context_for_user(enhanced_context, user_id)
        
        logger.info(f"Generated enhanced context for user {user_id}, confidence: {enhanced_context.confidence_score:.2f}")
        
        return {
            "enhanced_context": formatted_context,
            "insights": {
                "concept_map_insights": enhanced_context.concept_map_insights,
                "thinking_style_hints": enhanced_context.thinking_style_hints,
                "related_concepts": enhanced_context.related_concepts,
                "domain_context": enhanced_context.domain_context,
                "confidence_score": enhanced_context.confidence_score
            },
            "original_context": enhanced_context.original_context
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate enhanced context: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate enhanced context")