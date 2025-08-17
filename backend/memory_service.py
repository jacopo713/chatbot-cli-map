"""
Memory Service for Chatbot CLI Map

Implements a scalable memory system using:
- Cohere for text embeddings
- Pinecone for vector storage and retrieval
- Conversation memory with semantic search
"""

import os
import asyncio
import hashlib
import json
import logging
import unicodedata
from datetime import datetime
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass

import cohere
from pinecone import Pinecone
from pydantic import BaseModel
from zai import ZaiClient

logger = logging.getLogger(__name__)

@dataclass
class MemoryItem:
    """Represents a memory item to be stored or retrieved"""
    content: str
    metadata: Dict[str, Any]
    timestamp: datetime
    conversation_id: Optional[str] = None
    message_type: str = "chat"  # chat, system, context, etc.
    
class MemoryConfig(BaseModel):
    """Configuration for memory service"""
    cohere_api_key: str
    pinecone_api_key: str
    pinecone_index_name: str = "chatbot-cli-map"
    pinecone_host: str = "https://chatbot-cli-map-mp69iv8.svc.aped-4627-b74a.pinecone.io"
    embedding_model: str = "embed-multilingual-v3.0"
    embedding_dimension: int = 1024
    max_memory_items: int = 100
    similarity_threshold: float = 0.25  # Lowered threshold for better recall
    query_top_k: int = 24  # Higher top_k for better filtering
    # AI Classification
    ai_api_key: str = ""
    ai_model: str = "claude-3-5-haiku-20241022"  # Fast and efficient for classification

class MemoryService:
    """
    Scalable memory service for the chatbot.
    
    Features:
    - Semantic similarity search
    - Conversation context preservation  
    - Project-specific memory isolation
    - Configurable retention policies
    """
    
    def __init__(self, config: MemoryConfig):
        self.config = config
        self.cohere_client = None
        self.pinecone_client = None
        self.index = None
        self.ai_client = None
        self._initialized = False
        
    async def initialize(self) -> None:
        """Initialize the memory service connections"""
        if self._initialized:
            return
            
        try:
            # Initialize Cohere client
            self.cohere_client = cohere.ClientV2(api_key=self.config.cohere_api_key)
            
            # Initialize Pinecone
            self.pinecone_client = Pinecone(api_key=self.config.pinecone_api_key)
            self.index = self.pinecone_client.Index(
                name=self.config.pinecone_index_name,
                host=self.config.pinecone_host
            )
            
            # Initialize AI client for classification (optional)
            if self.config.ai_api_key:
                self.ai_client = ZaiClient(api_key=self.config.ai_api_key)
                logger.info("AI classification client initialized")
            else:
                logger.warning("No AI API key provided, falling back to rule-based classification")
            
            # Test connections
            await self._test_connections()
            self._initialized = True
            logger.info("Memory service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize memory service: {e}")
            raise
    
    async def _test_connections(self) -> None:
        """Test that both Cohere and Pinecone connections work"""
        try:
            # Test Cohere by generating a small embedding
            test_response = await asyncio.to_thread(
                self.cohere_client.embed,
                texts=["test"],
                model=self.config.embedding_model,
                input_type="search_document"
            )
            
            if not test_response.embeddings:
                raise Exception("Cohere embedding test failed")
                
            # Test Pinecone by checking index stats
            stats = await asyncio.to_thread(self.index.describe_index_stats)
            logger.info(f"Pinecone index stats: {stats.get('total_vector_count', 0)} vectors")
            
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            raise
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text for consistent hashing"""
        return unicodedata.normalize("NFKC", text).strip().lower()
    
    def _make_memory_id(self, kind: str, content: str, scope: str) -> str:
        """Generate deterministic ID for memory item"""
        normalized_content = self._normalize_text(content)
        base = f"{kind}|{scope}|{normalized_content}"
        return hashlib.sha1(base.encode("utf-8")).hexdigest()
    
    async def _embed_doc(self, text: str) -> List[float]:
        """Create embedding for document storage using Cohere"""
        if not self._initialized:
            await self.initialize()
            
        try:
            response = await asyncio.to_thread(
                self.cohere_client.embed,
                texts=[text],
                model=self.config.embedding_model,
                input_type="search_document",  # Optimized for document storage
                truncate="RIGHT"
            )
            
            embedding = self._extract_embedding(response)
            
            # Sanity check logging
            vector_len = len(embedding)
            vector_norm = sum(v*v for v in embedding) ** 0.5
            logger.info(f"embed_doc len={vector_len} norm={vector_norm:.3f} text='{text[:50]}...'")
            
            return embedding
            
        except Exception as e:
            logger.error(f"Failed to create document embedding: {e}")
            raise
    
    async def _embed_query(self, text: str) -> List[float]:
        """Create embedding for query search using Cohere"""
        if not self._initialized:
            await self.initialize()
            
        try:
            response = await asyncio.to_thread(
                self.cohere_client.embed,
                texts=[text],
                model=self.config.embedding_model,
                input_type="search_query",  # Optimized for query search
                truncate="RIGHT"
            )
            
            embedding = self._extract_embedding(response)
            
            # Sanity check logging
            vector_len = len(embedding)
            vector_norm = sum(v*v for v in embedding) ** 0.5
            logger.info(f"embed_query len={vector_len} norm={vector_norm:.3f} query='{text[:50]}...'")
            
            return embedding
            
        except Exception as e:
            logger.error(f"Failed to create query embedding: {e}")
            raise
    
    def _extract_embedding(self, response) -> List[float]:
        """Extract embedding from Cohere API response"""
        if not hasattr(response, 'embeddings'):
            raise Exception("No embeddings found in response")
        
        if hasattr(response.embeddings, 'float_'):
            # Cohere v5+ format: response.embeddings.float_
            embeddings_list = response.embeddings.float_
        elif hasattr(response.embeddings, 'embeddings'):
            # Fallback: response.embeddings.embeddings 
            embeddings_list = response.embeddings.embeddings
        elif isinstance(response.embeddings, list):
            # Direct list format
            embeddings_list = response.embeddings
        else:
            raise Exception(f"Unknown embeddings format: {type(response.embeddings)}")
        
        if not embeddings_list or len(embeddings_list) == 0:
            raise Exception("Empty embeddings list")
            
        return embeddings_list[0]
    
    async def store_memory(self, memory_item: MemoryItem) -> bool:
        """
        Store a memory item in the vector database
        
        Args:
            memory_item: The memory item to store
            
        Returns:
            bool: True if stored successfully
        """
        if not self._initialized:
            await self.initialize()
            
        try:
            # Generate embedding for the content using document embedding
            embedding = await self._embed_doc(memory_item.content)
            
            # Determine scope and kind
            scope = "global" if memory_item.conversation_id == "global" or memory_item.message_type == "personal" else f"chat:{memory_item.conversation_id or 'unknown'}"
            kind = memory_item.message_type or "chat"
            
            # Generate deterministic ID
            memory_id = self._make_memory_id(kind, memory_item.content, scope)
            
            # Prepare metadata with consistent field names
            metadata = {
                "text": memory_item.content,  # Canonical text field
                "content": memory_item.content,  # Keep for backward compatibility
                "timestamp": memory_item.timestamp.isoformat(),
                "scope": scope,
                "message_type": memory_item.message_type,
                "language": "it",  # Default to Italian
                **memory_item.metadata
            }
            
            # Add importance score for personal info
            if memory_item.message_type == "personal":
                metadata["importance"] = 0.8
            
            # Store in Pinecone
            await asyncio.to_thread(
                self.index.upsert,
                vectors=[{
                    "id": memory_id,
                    "values": embedding,
                    "metadata": metadata
                }]
            )
            
            logger.info(f"Stored memory item {memory_id} (type: {kind}, scope: {scope})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store memory: {e}")
            return False
    
    async def _query_namespace(self, vector: List[float], extra_filter: Dict = None) -> Any:
        """
        Query a specific namespace with filtering
        
        Args:
            vector: Query vector
            extra_filter: Additional filter conditions
            
        Returns:
            Pinecone query response
        """
        # Base filter: only include personal and chat memories, exclude chat_history from main retrieval
        base_filter = {"message_type": {"$in": ["personal", "chat"]}}
        
        if extra_filter:
            base_filter.update(extra_filter)
        
        return await asyncio.to_thread(
            self.index.query,
            vector=vector,
            top_k=self.config.query_top_k,
            include_metadata=True,
            filter=base_filter
        )
    
    async def retrieve_memories(
        self, 
        query: str, 
        conversation_id: Optional[str] = None,
        limit: int = 8,
        include_global: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant memories based on semantic similarity
        
        Args:
            query: The query text to search for
            conversation_id: Filter by conversation (None for all)
            limit: Maximum number of memories to return
            include_global: Whether to include global memories
            
        Returns:
            List of relevant memory items
        """
        if not self._initialized:
            await self.initialize()
            
        try:
            # Create embedding for the query using query-optimized embedding
            query_vector = await self._embed_query(query)
            
            # Query all relevant memories with backward compatibility
            # Build filter that works with both old (conversation_id) and new (scope) records
            filter_conditions = {"message_type": {"$in": ["personal", "chat"]}}
            
            if conversation_id:
                # Include both old format (conversation_id) and new format (scope)
                filter_conditions["$or"] = [
                    {"scope": "global"},  # New global records
                    {"scope": f"chat:{conversation_id}"},  # New conversation records
                    {"conversation_id": "global"},  # Old global records
                    {"conversation_id": conversation_id}  # Old conversation records
                ]
            else:
                # If no conversation_id, search global only
                filter_conditions["$or"] = [
                    {"scope": "global"},  # New global records
                    {"conversation_id": "global"}  # Old global records
                ]
            
            response = await asyncio.to_thread(
                self.index.query,
                vector=query_vector,
                top_k=self.config.query_top_k,
                include_metadata=True,
                filter=filter_conditions
            )
            
            matches = list(response.matches or [])
            
            # Process and deduplicate results
            kept = []
            seen = set()
            
            # Sort by score (descending)
            for match in sorted(matches, key=lambda x: x.score or 0, reverse=True):
                if (match.score or 0) < self.config.similarity_threshold:
                    continue
                    
                # Deduplicate on text content
                text_key = match.metadata.get("text") or match.metadata.get("content") or ""
                if text_key in seen:
                    continue
                seen.add(text_key)
                
                # Convert to standard format with backward compatibility
                scope = match.metadata.get("scope") or match.metadata.get("conversation_id", "unknown")
                memory_item = {
                    "id": match.id,
                    "content": text_key,
                    "text": text_key,  # Canonical field
                    "score": float(match.score or 0),
                    "timestamp": match.metadata.get("timestamp"),
                    "scope": scope,
                    "message_type": match.metadata.get("message_type", "chat"),
                    "role": match.metadata.get("role", "unknown"),
                    "metadata": {k: v for k, v in match.metadata.items() 
                               if k not in ["content", "text", "timestamp", "scope", "conversation_id", "message_type", "role"]}
                }
                
                kept.append(memory_item)
                
                if len(kept) >= limit:
                    break
            
            # Enhanced logging with hit details
            logger.info(f"Query: '{query[:50]}...' → {len(kept)}/{len(matches)} memories (threshold: {self.config.similarity_threshold})")
            for i, match in enumerate(kept, 1):
                logger.info(f"hit#{i} score={match['score']:.3f} text='{match['text'][:80]}...'")
            
            return kept
            
        except Exception as e:
            logger.error(f"Failed to retrieve memories: {e}")
            return []
    
    async def store_conversation_turn(
        self, 
        user_message: str, 
        ai_response: str, 
        conversation_id: str,
        additional_metadata: Dict[str, Any] = None
    ) -> bool:
        """
        Store a complete conversation turn (user + AI)
        
        Args:
            user_message: The user's message
            ai_response: The AI's response
            conversation_id: The conversation identifier
            additional_metadata: Extra metadata to store
            
        Returns:
            bool: True if stored successfully
        """
        metadata = additional_metadata or {}
        success_count = 0
        
        # Check if user message contains important personal info
        is_personal_info = await self._contains_personal_info(user_message)
        
        if is_personal_info:
            # For personal info, store ONLY as global canonical memory (avoid duplicates)
            canonical_content, category = await self._extract_canonical_facts(user_message)
            personal_memory = MemoryItem(
                content=canonical_content,
                metadata={
                    **metadata, 
                    "role": "user", 
                    "type": "personal_info",
                    "category": category,
                    "fact_type": canonical_content.split(":")[0] if ":" in canonical_content else "general"
                },
                timestamp=datetime.now(),
                conversation_id="global",
                message_type="personal"
            )
            
            if await self.store_memory(personal_memory):
                success_count += 1
                logger.info(f"Stored {category} personal info: {canonical_content[:50]}...")
        else:
            # For regular messages, store in chat context
            user_memory = MemoryItem(
                content=user_message,
                metadata={**metadata, "role": "user"},
                timestamp=datetime.now(),
                conversation_id=conversation_id,
                message_type="chat"
            )
            
            if await self.store_memory(user_memory):
                success_count += 1
        
        # Store AI response only in chat_history namespace (separate from personal memory)
        ai_memory = MemoryItem(
            content=ai_response,
            metadata={**metadata, "role": "assistant"},
            timestamp=datetime.now(),
            conversation_id=conversation_id,
            message_type="chat_history"  # Mark as chat history to exclude from personal memory retrieval
        )
        
        if await self.store_memory(ai_memory):
            success_count += 1
            
        return success_count >= 2  # At least user + ai messages stored
    
    async def _ai_extract_personal_facts(self, message: str) -> dict:
        """Use AI to extract personal facts from message"""
        if not self.ai_client:
            return {"is_personal_fact": False, "extracted_facts": [], "confidence": 0.0}
        
        try:
            prompt = f"""Analizza questo messaggio e determina se contiene FATTI PERSONALI verificabili dell'utente.

MESSAGGIO: "{message}"

REGOLE:
1. FATTI = affermazioni su sé stesso (nome, lavoro, preferenze, esperienze)
2. NON FATTI = domande, richieste, opinioni generali, saluti
3. Esempi FATTI: "Mi chiamo Marco", "Lavoro come sviluppatore", "Mi piace la pizza"
4. Esempi NON FATTI: "Come mi chiamo?", "Cosa pensi di...", "Ciao", "Grazie"

Rispondi SOLO con questo JSON:
{{
    "is_personal_fact": true/false,
    "extracted_facts": [
        {{"type": "name", "value": "Marco", "canonical": "user_name:Marco"}},
        {{"type": "job", "value": "sviluppatore", "canonical": "user_job:sviluppatore"}},
        {{"type": "preference", "value": "pizza", "canonical": "user_likes:pizza"}}
    ],
    "confidence": 0.95
}}

Tipi validi: name, job, location, preference, skill, age, hobby, experience"""

            response = await asyncio.to_thread(
                self.ai_client.chat.completions.create,
                model=self.config.ai_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1  # Low temperature for consistent classification
            )
            
            content = response.choices[0].message.content.strip()
            
            # Try to parse JSON response
            try:
                import json
                result = json.loads(content)
                
                # Validate structure
                if not isinstance(result, dict):
                    raise ValueError("Response is not a dict")
                    
                # Ensure required fields exist with defaults
                result.setdefault("is_personal_fact", False)
                result.setdefault("extracted_facts", [])
                result.setdefault("confidence", 0.0)
                
                # Validate confidence range
                result["confidence"] = max(0.0, min(1.0, float(result["confidence"])))
                
                logger.info(f"AI classification: {result['is_personal_fact']} (confidence: {result['confidence']:.2f})")
                return result
                
            except (json.JSONDecodeError, ValueError, KeyError) as e:
                logger.warning(f"Failed to parse AI response: {e}, content: {content[:100]}")
                return {"is_personal_fact": False, "extracted_facts": [], "confidence": 0.0}
            
        except Exception as e:
            logger.error(f"AI classification failed: {e}")
            return {"is_personal_fact": False, "extracted_facts": [], "confidence": 0.0}
    
    async def _contains_personal_info(self, message: str) -> bool:
        """Check if message contains personal information worth storing globally using AI"""
        if not self.ai_client:
            # Fallback to rule-based for backward compatibility
            return self._rule_based_personal_check(message)
        
        try:
            # Use AI classification
            result = await self._ai_extract_personal_facts(message)
            return result["is_personal_fact"] and result["confidence"] > 0.6
        except Exception as e:
            logger.warning(f"AI classification failed, falling back to rules: {e}")
            return self._rule_based_personal_check(message)
    
    def _rule_based_personal_check(self, message: str) -> bool:
        """Fallback rule-based personal info detection"""
        message_lower = message.lower().strip()
        
        # Skip questions - they are not personal facts
        if any(q in message_lower for q in ["come mi chiamo", "qual è il mio nome", "chi sono", "come sono", "cosa faccio"]):
            return False
        
        # Skip generic questions
        if message_lower.endswith("?") and any(w in message_lower[:10] for w in ["come", "cosa", "quando", "dove", "perché", "chi"]):
            return False
        
        # Patterns that indicate personal information (statements, not questions)
        personal_patterns = [
            "mi chiamo", "il mio nome è", "nome è",  
            "lavoro come", "lavoro in", "sono un", "sono una",
            "faccio il", "faccio la", "studio", "abito a", "vivo a",
            "mi piace", "preferisco", "amo", "odio",
            "sono bravo in", "mi occupo di", "ho anni"
        ]
        
        return any(pattern in message_lower for pattern in personal_patterns)
    
    async def _extract_canonical_facts(self, message: str) -> tuple[str, str]:
        """Extract canonical facts from personal information message using AI when available
        
        Returns:
            tuple: (canonical_fact, category)
        """
        if not self.ai_client:
            # Fallback to rule-based extraction
            fact = self._rule_based_canonical_extraction(message)
            category = self._determine_category_from_fact(fact)
            return fact, category
        
        try:
            # Use AI to extract facts
            result = await self._ai_extract_personal_facts(message)
            
            if result["extracted_facts"]:
                # Use the first canonical fact from AI
                first_fact = result["extracted_facts"][0]
                canonical = first_fact.get("canonical", "")
                category = self._determine_category_from_fact(canonical)
                if canonical:
                    return canonical, category
            
            # If AI didn't extract anything useful, fall back to rules
            fact = self._rule_based_canonical_extraction(message)
            category = self._determine_category_from_fact(fact)
            return fact, category
            
        except Exception as e:
            logger.warning(f"AI extraction failed, falling back to rules: {e}")
            fact = self._rule_based_canonical_extraction(message)
            category = self._determine_category_from_fact(fact)
            return fact, category
    
    def _rule_based_canonical_extraction(self, message: str) -> str:
        """Rule-based canonical fact extraction (fallback)"""
        message_lower = message.lower().strip()
        
        # Extract name
        if "mi chiamo" in message_lower:
            # "Mi chiamo Marco" -> extract "Marco"
            parts = message_lower.split("mi chiamo")
            if len(parts) > 1:
                name = parts[1].strip().split()[0].capitalize()
                return f"user_name:{name}"
        
        if "il mio nome è" in message_lower:
            parts = message_lower.split("il mio nome è")
            if len(parts) > 1:
                name = parts[1].strip().split()[0].capitalize()
                return f"user_name:{name}"
        
        # Extract profession/work
        if "lavoro come" in message_lower:
            parts = message_lower.split("lavoro come")
            if len(parts) > 1:
                job = parts[1].strip()
                return f"user_job:{job}"
        
        if "sono un" in message_lower or "sono una" in message_lower:
            if "sono un" in message_lower:
                parts = message_lower.split("sono un")
            else:
                parts = message_lower.split("sono una")
            if len(parts) > 1:
                role = parts[1].strip()
                return f"user_role:{role}"
        
        # Extract preferences
        if "mi piace" in message_lower:
            parts = message_lower.split("mi piace")
            if len(parts) > 1:
                preference = parts[1].strip()
                return f"user_likes:{preference}"
        
        if "preferisco" in message_lower:
            parts = message_lower.split("preferisco")
            if len(parts) > 1:
                preference = parts[1].strip()
                return f"user_prefers:{preference}"
        
        # Extract location
        if "abito a" in message_lower or "vivo a" in message_lower:
            if "abito a" in message_lower:
                parts = message_lower.split("abito a")
            else:
                parts = message_lower.split("vivo a")
            if len(parts) > 1:
                location = parts[1].strip()
                return f"user_location:{location}"
        
        # If no specific pattern matches, return original message but cleaned
        return message.strip()
    
    def _determine_category_from_fact(self, fact: str) -> str:
        """Determine category from canonical fact"""
        fact_lower = fact.lower()
        
        # Personal info categories
        if any(prefix in fact_lower for prefix in ["user_name:", "user_age:", "user_location:"]):
            return "personal"
        
        # Work related
        if any(prefix in fact_lower for prefix in ["user_job:", "user_role:", "user_skill:"]):
            return "work"
        
        # Health related
        if any(prefix in fact_lower for prefix in ["user_condition:", "anemia", "ocd", "anxiety", "depression"]):
            return "health"
        
        # Hobbies and preferences
        if any(prefix in fact_lower for prefix in ["user_likes:", "user_prefers:", "user_dislikes:"]):
            return "hobby"
        
        # Relationships
        if any(prefix in fact_lower for prefix in ["user_relationship:", "married", "single", "family"]):
            return "relationships"
        
        # Goals and aspirations
        if any(prefix in fact_lower for prefix in ["user_goal:", "wants to", "plans to"]):
            return "goals"
        
        # Default category
        return "general"
    
    async def get_conversation_context(
        self, 
        current_message: str, 
        conversation_id: str, 
        context_limit: int = 5
    ) -> str:
        """
        Get relevant conversation context for the current message
        
        Args:
            current_message: The current user message
            conversation_id: The conversation ID
            context_limit: Maximum number of context items
            
        Returns:
            Formatted context string
        """
        memories = await self.retrieve_memories(
            query=current_message,
            conversation_id=conversation_id,
            limit=context_limit,
            include_global=True
        )
        
        if not memories:
            return ""
        
        context_parts = ["## Contesto dalla memoria:"]
        
        for memory in memories:
            timestamp = memory.get("timestamp", "")
            role = memory.get("role", "unknown")
            content = memory.get("text", memory.get("content", ""))  # Prefer canonical 'text' field
            score = memory.get("score", 0.0)
            message_type = memory.get("message_type", "")
            
            # Format with score and type for better debugging
            type_indicator = f" [{message_type}]" if message_type else ""
            context_parts.append(f"**{role.title()}**{type_indicator} (score: {score:.2f}): {content}")
        
        return "\n".join(context_parts)
    
    async def cleanup_old_memories(self, days_to_keep: int = 30) -> int:
        """
        Clean up old memories (placeholder for future implementation)
        
        Args:
            days_to_keep: Number of days of memories to retain
            
        Returns:
            Number of memories cleaned up
        """
        # This would be implemented based on timestamp filtering
        # For now, just return 0 as placeholder
        logger.info(f"Memory cleanup requested for memories older than {days_to_keep} days")
        return 0

# Global memory service instance
_memory_service: Optional[MemoryService] = None

def get_memory_service() -> Optional[MemoryService]:
    """Get the global memory service instance"""
    return _memory_service

async def initialize_memory_service() -> MemoryService:
    """Initialize and return the global memory service"""
    global _memory_service
    
    if _memory_service is None:
        config = MemoryConfig(
            cohere_api_key=os.getenv("COHERE_API_KEY", ""),
            pinecone_api_key=os.getenv("PINECONE_API_KEY", ""),
            pinecone_index_name=os.getenv("PINECONE_INDEX", "chatbot-cli-map"),
            pinecone_host=os.getenv("PINECONE_HOST", "https://chatbot-cli-map-mp69iv8.svc.aped-4627-b74a.pinecone.io"),
            ai_api_key=os.getenv("ZAI_API_KEY", "")  # Use ZAI API key for AI classification
        )
        
        if not config.cohere_api_key or not config.pinecone_api_key:
            logger.warning("Memory service API keys not configured, memory features disabled")
            return None
            
        _memory_service = MemoryService(config)
        await _memory_service.initialize()
    
    return _memory_service