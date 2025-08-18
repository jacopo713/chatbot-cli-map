from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import os
from dotenv import load_dotenv
import asyncio
import logging
import time
from typing import List, Dict, AsyncGenerator, Any, Optional
from pathlib import Path

from zai import ZaiClient
from helpers_bandit import ensure_stats_initialized  # opzionale: safe no-op se non usato
from memory_service import initialize_memory_service, get_memory_service
from hybrid_memory_service import initialize_hybrid_memory_service, get_hybrid_memory_service
from enhanced_memory_service import get_enhanced_memory_service
from firebase_enhanced_memory_service import get_firebase_enhanced_memory_service
from firebase_endpoints import router as firebase_router
# Simplified backend without multi-agent system



# ──────────────────────────────────────────────────────────────────────────────
# Logging
# ──────────────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    handlers=[logging.FileHandler("backend.log"), logging.StreamHandler()],
)
logger = logging.getLogger("chatbot-api")

# ──────────────────────────────────────────────────────────────────────────────
# Env & App
# ──────────────────────────────────────────────────────────────────────────────
def _load_env_fallback() -> None:
    try:
        p = Path("backend/.env")
        if p.exists():
            for raw in p.read_text(encoding="utf-8").splitlines():
                s = raw.strip()
                if not s or s.startswith("#") or "=" not in s:
                    continue
                k, v = s.split("=", 1)
                k = k.strip(); v = v.strip()
                if k and (k not in os.environ):
                    os.environ[k] = v
    except Exception:
        pass

try:
    load_dotenv()
except Exception:
    _load_env_fallback()
else:
    _load_env_fallback()

app = FastAPI(title="Chatbot CLI Map API")

# Include Firebase routes
app.include_router(firebase_router)

FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:3000")
MODEL_NAME = os.getenv("ZAI_MODEL", "glm-4.5")
DEFAULT_TEMPERATURE = float(os.getenv("ZAI_TEMPERATURE", "0.7"))
DEFAULT_TOP_P = float(os.getenv("ZAI_TOP_P", "0.9"))

# Memory system configuration
USE_HYBRID_MEMORY = os.getenv("USE_HYBRID_MEMORY", "true").lower() == "true"

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000", 
        "http://localhost:3001",
        "http://localhost:3002",
        "https://chatbot-cli-map.vercel.app",
        "https://*.vercel.app",
        "https://thinkturing.com",
        "https://*.thinkturing.com"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Intent", "X-Variant-ID"],
)

api_key = os.getenv("ZAI_API_KEY")
if not api_key:
    logger.error("ZAI_API_KEY non è configurata")
    raise ValueError("ZAI_API_KEY non è configurata")

api_url = os.getenv("API_URL") or os.getenv("ZAI_API_URL") or os.getenv("ZAI_BASE_URL")
if api_url:
    try:
        client = ZaiClient(api_key=api_key, base_url=api_url)
    except TypeError:
        client = ZaiClient(api_key=api_key, api_url=api_url)  # type: ignore
else:
    client = ZaiClient(api_key=api_key)

# Rating storage (facoltativo)
RATINGS_PATH = Path("backend/ratings.jsonl")
RATINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
_write_lock = asyncio.Lock()

try:
    ensure_stats_initialized()
except Exception:
    pass

# Initialize memory services
memory_service = None
hybrid_memory_service = None
enhanced_memory_service = None
firebase_enhanced_memory_service = None

# Simplified backend - no multi-agent system needed

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    global memory_service, hybrid_memory_service, enhanced_memory_service, firebase_enhanced_memory_service
    try:
        # Initialize Firebase service FIRST (independent from memory services)
        try:
            logger.info("Initializing FIREBASE service...")
            from firebase_service import get_firebase_service
            firebase_service = await get_firebase_service()
            if firebase_service:
                logger.info("🔥 Firebase service initialized")
            else:
                logger.warning("Firebase service failed to initialize")
        except Exception as e:
            logger.warning(f"Firebase service initialization failed (non-critical): {e}")
            firebase_service = None
        
        # Initialize memory services with error handling
        try:
            if USE_HYBRID_MEMORY:
                logger.info("Initializing HYBRID memory service...")
                hybrid_memory_service = await initialize_hybrid_memory_service()
                if hybrid_memory_service:
                    logger.info("🚀 Hybrid memory service initialized successfully")
                    
                    # Initialize enhanced memory service with concept map integration
                    logger.info("Initializing ENHANCED memory service with concept map integration...")
                    enhanced_memory_service = await get_enhanced_memory_service(firebase_service=firebase_service)
                    if enhanced_memory_service:
                        logger.info("🧠 Enhanced memory service with concept map integration initialized")
                    else:
                        logger.warning("Enhanced memory service failed to initialize")
                    
                    # Initialize Firebase enhanced memory service
                    logger.info("Initializing FIREBASE enhanced memory service...")
                    firebase_enhanced_memory_service = await get_firebase_enhanced_memory_service()
                    if firebase_enhanced_memory_service:
                        logger.info("🔥 Firebase enhanced memory service initialized")
                    else:
                        logger.warning("Firebase enhanced memory service failed to initialize")
                else:
                    logger.warning("Hybrid memory service not available - falling back to standard")
                    memory_service = await initialize_memory_service()
            else:
                logger.info("Initializing STANDARD memory service...")
                memory_service = await initialize_memory_service()
                if memory_service:
                    logger.info("Memory service initialized successfully")
            
            if not memory_service and not hybrid_memory_service:
                logger.warning("No memory service available - API keys may be missing")
        except Exception as e:
            logger.warning(f"Memory service initialization failed (non-critical): {e}")
            # Continue without memory service
        
        # Simplified backend - direct GLM 4.5 calls only
        logger.info("✅ Simplified backend ready with direct GLM 4.5 calls")
            
    except Exception as e:
        logger.warning(f"Some services failed to initialize: {e}")
        # Don't block server startup

# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────
def _prune_history(history: List[Dict[str, str]], max_chars: int = 25000) -> List[Dict[str, str]]:
    if not isinstance(history, list):
        return []
    pruned: List[Dict[str, str]] = []
    used = 0
    for item in reversed(history):
        try:
            role = str(item.get("role", "")).lower()
            content = str(item.get("content", ""))
        except Exception:
            continue
        if role not in ("user", "assistant"):
            continue
        cost = len(role) + len(content) + 4
        if used + cost > max_chars:
            break
        pruned.append({"role": role, "content": content})
        used += cost
    pruned.reverse()
    return pruned

async def call_model_stream(messages: List[Dict[str, Any]], **kwargs) -> AsyncGenerator[str, None]:
    """
    Streaming verso Z.AI senza prompt di sistema.
    kwargs: temperature, top_p
    """
    temperature = kwargs.get("temperature", DEFAULT_TEMPERATURE)
    top_p = kwargs.get("top_p", DEFAULT_TOP_P)
    logger.info("LLM stream call: model=%s, T=%.2f, top_p=%.2f, msgs=%d", MODEL_NAME, temperature, top_p, len(messages))

    def sync_stream_call():
        return client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            stream=True,
            temperature=temperature,
            top_p=top_p,
        )

    try:
        stream_response = await asyncio.to_thread(sync_stream_call)
        chunk_count = 0
        for chunk in stream_response:
            if hasattr(chunk, "choices") and chunk.choices:
                delta = chunk.choices[0].delta
                if hasattr(delta, "content") and delta.content:
                    chunk_count += 1
                    yield delta.content
                    # Log streaming progress periodically
                    if chunk_count % 20 == 0:
                        logger.debug(f"Streamed {chunk_count} chunks")
        logger.info(f"Stream completed with {chunk_count} total chunks")
    except Exception as e:
        logger.exception("Errore nella chiamata streaming al modello: %s", e)
        yield f"Errore: {str(e)}"

async def call_model_once(messages: List[Dict[str, Any]], **kwargs) -> str:
    """
    Chiamata non-streaming: restituisce l'intero contenuto come stringa.
    """
    temperature = kwargs.get("temperature", DEFAULT_TEMPERATURE)
    top_p = kwargs.get("top_p", DEFAULT_TOP_P)
    logger.info("LLM call (one-shot): model=%s, T=%.2f, top_p=%.2f, msgs=%d", MODEL_NAME, temperature, top_p, len(messages))

    def sync_call():
        return client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            temperature=temperature,
            top_p=top_p,
        )

    try:
        resp = await asyncio.to_thread(sync_call)
        content = None
        if hasattr(resp, "choices") and resp.choices:
            choice = resp.choices[0]
            if hasattr(choice, "message") and getattr(choice, "message") is not None:
                msg = choice.message
                if hasattr(msg, "content") and msg.content:
                    content = msg.content
            if content is None and hasattr(choice, "text") and choice.text:
                content = choice.text
        if content is None and isinstance(resp, dict):
            try:
                content = resp["choices"][0]["message"]["content"]
            except Exception:
                try:
                    content = resp["choices"][0]["text"]
                except Exception:
                    pass
        return str(content or "").strip()
    except Exception as e:
        logger.exception("Errore nella chiamata non-streaming al modello: %s", e)
        return ""

# ──────────────────────────────────────────────────────────────────────────────
# /api/chat (streaming) — nessun system message, niente “regole prompt” inline
# ──────────────────────────────────────────────────────────────────────────────
@app.post("/api/chat")
async def chat(request: Request):
    """
    Accetta:
      - message: str
      - history: [{role, content}]
      - context_files: [{path, language, content}] (opzionale)
      - project_name: str | None (opzionale)
      - concept_map_context: str | None (opzionale)
      - conversation_id: str | None (unused lato server)
      - temperature/top_p: override opzionale
    """
    try:
        data = await request.json()
    except Exception as e:
        logger.error("JSON parse error: %s", e)
        return StreamingResponse(iter(["❌ **Errore generale**: JSON non valido"]), media_type="text/plain")

    message: str = data.get("message", "") or "Hello"
    history: List[Dict[str, str]] = data.get("history", []) or []
    context_files = data.get("context_files", []) or []
    project_name: Optional[str] = data.get("project_name")
    concept_map_context: Optional[str] = data.get("concept_map_context")
    active_concept_map_id: Optional[str] = data.get("active_concept_map_id")
    user_id: Optional[str] = data.get("user_id")  # Added user_id support
    temperature = data.get("temperature", DEFAULT_TEMPERATURE)
    top_p = data.get("top_p", DEFAULT_TOP_P)

    start_time = time.time()
    logger.info("CHAT in: msg='%.60s' hist=%d", message[:60], len(history))

    # 1) history (potata)
    messages: List[Dict[str, str]] = []
    if history:
        pruned_history = _prune_history(history, max_chars=15000)
        messages.extend(pruned_history)

    # 2) Get conversation_id early for Chain of Thought
    conversation_id = data.get("conversation_id", "default")
    
    # No Chain of Thought reasoning - simplified approach

    # Simplified memory retrieval - no complex parallel processing
    memory_context = ""
    
    # Try to get basic memory context if available
    active_memory_service = enhanced_memory_service or hybrid_memory_service or memory_service
    if active_memory_service:
        try:
            logger.info(f"Retrieving memory context for: '{message[:50]}...'")
            
            if enhanced_memory_service:
                enhanced_context = await enhanced_memory_service.get_enhanced_conversation_context(
                    current_message=message,
                    conversation_id=conversation_id,
                    context_limit=3,
                    active_concept_map_id=active_concept_map_id,
                    user_id=user_id
                )
                memory_context = enhanced_memory_service.format_enhanced_context(enhanced_context)
            elif active_memory_service:
                memory_context = await active_memory_service.get_conversation_context(
                    current_message=message,
                    conversation_id=conversation_id,
                    context_limit=10
                )
            
            if memory_context:
                logger.info(f"Memory context retrieved: {len(memory_context)} chars")
            else:
                logger.info("No relevant memory context found")
                
        except Exception as e:
            logger.warning(f"Memory retrieval failed: {e}")
            memory_context = ""

    # 4) contesto opzionale come messaggio 'user' (dati, non istruzioni)
    context_chunks: List[str] = []
    
    # No reasoning context needed
    
    # Add memory context if available
    if memory_context:
        context_chunks.append(memory_context)
    if project_name:
        context_chunks.append(f"Contesto progetto: {project_name}")

    if context_files:
        max_chars = 50000
        total = 0
        file_bits = []
        for f in context_files:
            try:
                path = str(f.get("path", "")).strip()
                language = str(f.get("language", "")).strip()
                content = str(f.get("content", ""))
            except Exception:
                continue
            if not path or not content:
                continue
            block = f"File: {path}\n```{language}\n{content}\n```"
            if total + len(block) > max_chars:
                break
            file_bits.append(block)
            total += len(block)
        if file_bits:
            context_chunks.append("File del progetto:\n" + "\n\n".join(file_bits))

    if concept_map_context:
        cm = (concept_map_context or "").strip()
        if cm:
            context_chunks.append("Mappa concettuale:\n" + cm[:10000])

    if context_chunks:
        full_context = "\n\n".join(context_chunks)
        messages.append({"role": "user", "content": full_context})
        logger.info(f"CONTEXT SENT TO AI ({len(full_context)} chars):")
        logger.info(f"FULL CONTEXT: {full_context}")

    # 3) messaggio utente corrente
    messages.append({"role": "user", "content": message})
    
    # Log total preparation time
    prep_duration = time.time() - start_time
    logger.info(f"Chat preparation completed in {prep_duration:.2f}s")

    # Simple API without reasoning

    async def stream_generator():
        try:
            logger.info("Stream start - msgs=%d", len(messages))
            
            # Send a small initial chunk to establish the connection
            yield ""
            
            # Accumulate the AI response for memory storage
            ai_response_parts = []
            
            async for chunk in call_model_stream(messages, temperature=temperature, top_p=top_p):
                ai_response_parts.append(chunk)
                yield chunk
                # Force flush the stream immediately
                await asyncio.sleep(0)

            # Store conversation in memory if available
            storage_service = enhanced_memory_service or hybrid_memory_service or memory_service
            if storage_service:
                try:
                    ai_response = "".join(ai_response_parts)
                    asyncio.create_task(
                        storage_service.store_conversation_turn(
                            user_message=message,
                            ai_response=ai_response,
                            conversation_id=conversation_id,
                            additional_metadata={"project_name": project_name}
                        )
                    )
                except Exception as e:
                    logger.warning(f"Failed to store memory: {e}")

            logger.info("Stream end")
        except Exception as e:
            logger.exception("Stream generator - errore: %s", e)
            yield f"❌ **Errore**: {str(e)}"

    return StreamingResponse(
        stream_generator(), 
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        }
    )

# Multi-agent endpoints removed - simplified backend uses only direct GLM 4.5 calls

# ──────────────────────────────────────────────────────────────────────────────
# Memory Management Endpoints
# ──────────────────────────────────────────────────────────────────────────────
@app.get("/api/memory/status")
async def memory_status():
    """Get memory service status including concept map enhancements"""
    
    # Check enhanced service first
    if enhanced_memory_service:
        try:
            stats = enhanced_memory_service.get_stats()
            return {
                "available": True,
                "service": "cohere + pinecone + concept_maps",
                "model": "embed-multilingual-v3.0",
                "dimensions": 1024,
                "type": "enhanced",
                "features": [
                    "importance_classification",
                    "sliding_window_buffer", 
                    "conversation_summarization",
                    "multi_tier_storage",
                    "ttl_support",
                    "concept_map_integration",
                    "thinking_pattern_analysis",
                    "semantic_metadata_enhancement",
                    "personalized_context_generation"
                ],
                "enhancement_features": {
                    "concept_map_analysis": True,
                    "thinking_pattern_extraction": True,
                    "semantic_relationship_mapping": True,
                    "domain_expertise_detection": True,
                    "causal_chain_reasoning": True,
                    "hierarchical_thinking_support": True
                },
                "stats": stats
            }
        except Exception as e:
            logger.error(f"Failed to get enhanced memory stats: {e}")
    
    # Fallback to base services
    active_service = hybrid_memory_service or memory_service
    
    if not active_service:
        return {"available": False, "reason": "No memory service initialized"}
    
    base_info = {
        "available": True,
        "service": "cohere + pinecone",
        "model": "embed-multilingual-v3.0",
        "dimensions": 1024
    }
    
    if hybrid_memory_service:
        stats = hybrid_memory_service.get_stats()
        return {
            **base_info,
            "type": "hybrid",
            "features": [
                "importance_classification",
                "sliding_window_buffer", 
                "conversation_summarization",
                "multi_tier_storage",
                "ttl_support"
            ],
            "stats": stats
        }
    else:
        return {
            **base_info,
            "type": "standard"
        }

@app.post("/api/memory/search")
async def search_memories(request: Request):
    """
    Search memories by query
    Input: { query: str, conversation_id?: str, limit?: int }
    """
    active_service = hybrid_memory_service or memory_service
    
    if not active_service:
        return {"error": "Memory service not available", "memories": []}
    
    try:
        data = await request.json()
        query = data.get("query", "").strip()
        conversation_id = data.get("conversation_id")
        limit = data.get("limit", 10)
        
        if not query:
            return {"error": "Query is required", "memories": []}
        
        # Use appropriate method based on service type
        if hybrid_memory_service:
            memories = await hybrid_memory_service.retrieve_memories(
                query=query,
                conversation_id=conversation_id,
                limit=min(limit, 100),
                include_recent=True
            )
        else:
            memories = await memory_service.retrieve_memories(
                query=query,
                conversation_id=conversation_id,
                limit=min(limit, 100),
                include_global=True
            )
        
        service_type = "hybrid" if hybrid_memory_service else "standard"
        return {
            "memories": memories, 
            "count": len(memories),
            "service_type": service_type
        }
        
    except Exception as e:
        logger.exception("Error searching memories: %s", e)
        return {"error": str(e), "memories": []}


# ──────────────────────────────────────────────────────────────────────────────
# Memory Management Endpoints
# ──────────────────────────────────────────────────────────────────────────────

@app.get("/api/memory/analyze")
async def analyze_memories():
    """Analyze memory statistics by type, role, and scope"""
    try:
        # Try hybrid memory service first
        hybrid_service = get_hybrid_memory_service()
        if hybrid_service:
            memory_service = hybrid_service
        else:
            memory_service = get_memory_service()
            
        if not memory_service:
            return {"error": "Memory service not available", "stats": {}}
        
        # Get index stats first
        stats = await asyncio.to_thread(memory_service.index.describe_index_stats)
        total_vectors = stats.get('total_vector_count', 0)
        
        # Query all memories with no filter to get full dataset
        dummy_vector = [0.1] * 1024
        response = await asyncio.to_thread(
            memory_service.index.query,
            vector=dummy_vector,
            top_k=1000,  # Get up to 1000 records for analysis
            include_metadata=True
        )
        
        # Analyze by categories
        analysis = {
            "total_memories": total_vectors,
            "analyzed_sample": len(response.matches),
            "relevant_memories": 0,  # Will count only non-chat_history
            "by_message_type": {},
            "by_category": {},  # New: analyze by category field
            "by_role": {},
            "by_scope": {},
            "by_conversation": {},
            "recent_memories": []
        }
        
        conversation_counts = {}
        
        for match in response.matches:
            metadata = match.metadata or {}
            
            # Skip chat_history from analysis (AI responses should not appear in main stats)
            msg_type = metadata.get("message_type", "unknown")
            if msg_type == "chat_history":
                continue
            
            # Count by message type
            analysis["by_message_type"][msg_type] = analysis["by_message_type"].get(msg_type, 0) + 1
            analysis["relevant_memories"] += 1
            
            # Count by category (new field with actual categorization)
            category = metadata.get("category", "uncategorized")
            analysis["by_category"][category] = analysis["by_category"].get(category, 0) + 1
            
            # Count by role
            role = metadata.get("role", "unknown")
            analysis["by_role"][role] = analysis["by_role"].get(role, 0) + 1
            
            # Count by scope (new) or conversation_id (old)
            scope = metadata.get("scope") or metadata.get("conversation_id", "unknown")
            analysis["by_scope"][scope] = analysis["by_scope"].get(scope, 0) + 1
            
            # Count conversations
            conv_id = metadata.get("conversation_id", "unknown")
            conversation_counts[conv_id] = conversation_counts.get(conv_id, 0) + 1
            
            # Add to recent memories (first 10) - only relevant memories
            if len(analysis["recent_memories"]) < 10:
                content = metadata.get("text") or metadata.get("content", "")
                analysis["recent_memories"].append({
                    "content": content[:100] + "..." if len(content) > 100 else content,
                    "type": msg_type,
                    "category": category,  # Add category to recent memories
                    "role": role,
                    "scope": scope,
                    "timestamp": metadata.get("timestamp", "")
                })
        
        # Add conversation stats
        analysis["by_conversation"] = dict(sorted(
            conversation_counts.items(), 
            key=lambda x: x[1], 
            reverse=True
        )[:20])  # Top 20 conversations
        
        return {"success": True, "stats": analysis}
        
    except Exception as e:
        logger.error(f"Failed to analyze memories: {e}")
        return {"error": str(e), "stats": {}}

@app.delete("/api/memory/clear")
async def clear_memories():
    """Clear all memories from the vector database"""
    try:
        # Try hybrid memory service first
        hybrid_service = get_hybrid_memory_service()
        if hybrid_service:
            memory_service = hybrid_service
        else:
            memory_service = get_memory_service()
            
        if not memory_service:
            return {"error": "Memory service not available"}
        
        # Get all vector IDs
        stats = await asyncio.to_thread(memory_service.index.describe_index_stats)
        total_count = stats.get('total_vector_count', 0)
        
        if total_count == 0:
            return {"success": True, "message": "No memories to clear", "deleted_count": 0}
        
        # Query to get all IDs (using dummy vector)
        dummy_vector = [0.1] * 1024
        response = await asyncio.to_thread(
            memory_service.index.query,
            vector=dummy_vector,
            top_k=10000,  # Large number to get all vectors
            include_metadata=False  # We only need IDs
        )
        
        # Delete all vectors by ID
        vector_ids = [match.id for match in response.matches]
        
        if vector_ids:
            await asyncio.to_thread(
                memory_service.index.delete,
                ids=vector_ids
            )
            
            logger.info(f"Cleared {len(vector_ids)} memories from vector database")
            return {
                "success": True, 
                "message": f"Successfully cleared {len(vector_ids)} memories",
                "deleted_count": len(vector_ids)
            }
        else:
            return {"success": True, "message": "No memories found to clear", "deleted_count": 0}
        
    except Exception as e:
        logger.error(f"Failed to clear memories: {e}")
        return {"error": str(e)}

@app.post("/api/memory/save-ai-response")
async def save_ai_response_manually(request: Request):
    """Manually save an AI response to memory when user finds it important"""
    try:
        data = await request.json()
        ai_response = data.get("ai_response", "")
        conversation_id = data.get("conversation_id", "unknown")
        user_message = data.get("user_message", "")
        
        if not ai_response:
            return {"error": "AI response is required"}
        
        # Try hybrid memory service first
        hybrid_service = get_hybrid_memory_service()
        if hybrid_service:
            success = await hybrid_service.store_ai_response_manually(
                ai_response=ai_response,
                conversation_id=conversation_id,
                user_message=user_message,
                additional_metadata={"saved_manually": True}
            )
            
            if success:
                logger.info(f"Manually saved AI response for conversation {conversation_id}")
                return {
                    "success": True,
                    "message": "AI response saved to memory successfully"
                }
            else:
                return {"error": "Failed to save AI response"}
        else:
            return {"error": "Memory service not available"}
            
    except Exception as e:
        logger.error(f"Failed to save AI response manually: {e}")
        return {"error": str(e)}

# ──────────────────────────────────────────────────────────────────────────────
# /api/health
# ──────────────────────────────────────────────────────────────────────────────
@app.get("/api/health")
async def health():
    return {"ok": True, "model": MODEL_NAME}

# Debug endpoint to check Firebase concept maps
@app.get("/api/debug/firebase-maps")
async def debug_firebase_maps():
    """Debug endpoint to check Firebase concept maps without authentication"""
    try:
        from firebase_service import get_firebase_service
        firebase_service = await get_firebase_service()
        if not firebase_service:
            return {"error": "Firebase service not available"}
        
        # Check for any concept maps in the collection
        if not firebase_service._initialized:
            await firebase_service.initialize()
            
        maps_ref = firebase_service.db.collection('concept_maps')
        docs = maps_ref.stream()
        
        concept_maps = []
        for doc in docs:
            map_data = doc.to_dict()
            concept_maps.append({
                'id': doc.id,
                'userId': map_data.get('userId'),
                'title': map_data.get('title'),
                'nodeCount': len(map_data.get('nodes', [])),
                'edgeCount': len(map_data.get('edges', [])),
                'createdAt': map_data.get('createdAt'),
                'updatedAt': map_data.get('updatedAt')
            })
        
        return {
            "total_maps": len(concept_maps),
            "maps": concept_maps[:10]  # First 10 maps
        }
        
    except Exception as e:
        logger.error(f"Debug endpoint error: {e}")
        return {"error": str(e)}

# ──────────────────────────────────────────────────────────────────────────────
# Root endpoint
# ──────────────────────────────────────────────────────────────────────────────
@app.get("/")
async def root():
    return {"message": "Chatbot CLI Map API"}

@app.get("/api/")
async def api_root():
    return {"message": "Chatbot CLI Map API", "status": "running"}

if __name__ == "__main__":
    import uvicorn
    logger.info("Avvio server...")
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)

