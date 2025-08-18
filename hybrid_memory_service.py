"""
Hybrid Memory Service for Chatbot CLI Map

Implements an intelligent hybrid memory system with:
- Importance classification
- Sliding window buffer for recent messages
- Conversation summarization
- Multi-tier storage (recent/important/compressed)
- Smart retrieval with performance optimization
"""

import os
import asyncio
import hashlib
import json
import logging
import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any, Tuple, Deque
from dataclasses import dataclass
from collections import deque
from enum import Enum

import cohere
from pinecone import Pinecone
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class ImportanceLevel(Enum):
    """Message importance levels"""
    LOW = "low"           # 0.0 - 0.3: Small talk, confirmations
    MEDIUM = "medium"     # 0.3 - 0.7: Useful info, questions
    HIGH = "high"         # 0.7 - 1.0: Critical info, personal data, decisions
    
class StorageTier(Enum):
    """Storage tiers with different retention policies"""
    RECENT = "recent"         # Sliding window - 50 messages max
    IMPORTANT = "important"   # High importance - permanent
    MEDIUM_TERM = "medium"    # Medium importance - 30 days TTL
    COMPRESSED = "compressed" # Summarized chunks - permanent
    GLOBAL = "global"         # Personal info - permanent, cross-conversation

@dataclass
class HybridMemoryItem:
    """Enhanced memory item for hybrid system"""
    content: str
    metadata: Dict[str, Any]
    timestamp: datetime
    conversation_id: str
    message_type: str = "chat"
    importance: ImportanceLevel = ImportanceLevel.LOW
    storage_tier: StorageTier = StorageTier.RECENT
    ttl: Optional[datetime] = None
    
class HybridMemoryConfig(BaseModel):
    """Configuration for hybrid memory service"""
    cohere_api_key: str
    pinecone_api_key: str
    pinecone_index_name: str = "chatbot-cli-map"
    pinecone_host: str = "https://chatbot-cli-map-mp69iv8.svc.aped-4627-b74a.pinecone.io"
    embedding_model: str = "embed-multilingual-v3.0"
    embedding_dimension: int = 1024
    
    # Hybrid system parameters
    recent_buffer_size: int = 50
    similarity_threshold: float = 0.25
    importance_threshold_high: float = 0.7
    importance_threshold_medium: float = 0.4
    medium_term_ttl_days: int = 30
    summarization_chunk_size: int = 20

class MessageImportanceClassifier:
    """Classifies message importance using rule-based + pattern matching"""
    
    def __init__(self):
        # Personal information patterns (high importance)
        self.personal_patterns = [
            r"\bmi chiamo\b", r"\bil mio nome\b", r"\bsono [a-zA-Z]+\b",
            r"\blavoro come\b", r"\bfaccio il\b", r"\bstudio\b", r"\babito\b",
            r"\bho \d+ anni\b", r"\bsono nato\b", r"\bvivo a\b",
            r"\bmi piace\b", r"\bamo\b", r"\bodio\b", r"\bdetesto\b",
            r"\bpreferisc[oi]\b", r"\bmia passione\b", r"\bmio hobby\b",
            r"\bsono allergico\b", r"\bnon posso mangiare\b"
        ]
        
        # Decision/action patterns (high importance)
        self.decision_patterns = [
            r"\bdecido\b", r"\bscelgo\b", r"\bvoglio\b", r"\bdevo\b", 
            r"\bricordati\b", r"\bimportante\b", r"\bnon dimenticare\b",
            r"\bpiano\b", r"\bobbiettivo\b", r"\bstrategia\b"
        ]
        
        # Technical/project patterns (medium-high importance)  
        self.technical_patterns = [
            r"\bprogetto\b", r"\bcodice\b", r"\bapi\b", r"\bdatabase\b",
            r"\bfunzione\b", r"\balgoritmo\b", r"\barchitettura\b",
            r"\berr?ore\b", r"\bbug\b", r"\bproblema\b", r"\bsoluzione\b"
        ]
        
        # Question patterns (medium importance)
        self.question_patterns = [
            r"\bcome\b.*\?", r"\bperch[eé]\b.*\?", r"\bdove\b.*\?",
            r"\bquando\b.*\?", r"\bcosa\b.*\?", r"\bquale\b.*\?"
        ]
        
        # Low importance patterns
        self.low_patterns = [
            r"\bciao\b", r"\bgrazie\b", r"\bprego\b", r"\bva bene\b",
            r"\bsi\b", r"\bno\b", r"\bok\b", r"\bd'accordo\b", r"\bperfetto\b"
        ]
    
    def classify(self, message: str) -> Tuple[ImportanceLevel, float, Dict[str, Any]]:
        """Classify message importance
        
        Returns:
            Tuple of (ImportanceLevel, confidence_score, reasoning)
        """
        message_lower = message.lower()
        reasoning = {"patterns_matched": [], "factors": []}
        score = 0.0
        
        # Check personal information (highest priority)
        personal_matches = [p for p in self.personal_patterns if re.search(p, message_lower)]
        if personal_matches:
            score += 0.8
            reasoning["patterns_matched"].extend(personal_matches)
            reasoning["factors"].append("personal_info")
        
        # Check decisions/actions
        decision_matches = [p for p in self.decision_patterns if re.search(p, message_lower)]
        if decision_matches:
            score += 0.6
            reasoning["patterns_matched"].extend(decision_matches)
            reasoning["factors"].append("decision_action")
        
        # Check technical content
        tech_matches = [p for p in self.technical_patterns if re.search(p, message_lower)]
        if tech_matches:
            score += 0.4
            reasoning["patterns_matched"].extend(tech_matches) 
            reasoning["factors"].append("technical_content")
        
        # Check questions
        question_matches = [p for p in self.question_patterns if re.search(p, message_lower)]
        if question_matches:
            score += 0.3
            reasoning["patterns_matched"].extend(question_matches)
            reasoning["factors"].append("question")
            
        # Check low importance (reduces score)
        low_matches = [p for p in self.low_patterns if re.search(p, message_lower)]
        if low_matches and len(message.split()) <= 3:  # Short low-importance messages
            score *= 0.3
            reasoning["factors"].append("low_importance")
        
        # Message length factor
        word_count = len(message.split())
        if word_count > 20:  # Long messages tend to be more important
            score += 0.2
            reasoning["factors"].append("long_message")
        elif word_count < 5:  # Very short messages often less important
            score *= 0.8
            reasoning["factors"].append("short_message")
        
        # Normalize score to 0-1 range
        score = min(1.0, score)
        
        # Determine importance level
        if score >= 0.7:
            importance = ImportanceLevel.HIGH
        elif score >= 0.4:
            importance = ImportanceLevel.MEDIUM
        else:
            importance = ImportanceLevel.LOW
            
        reasoning["final_score"] = score
        
        return importance, score, reasoning

class ConversationSummarizer:
    """Summarizes conversation chunks using Cohere"""
    
    def __init__(self, cohere_client: cohere.ClientV2):
        self.client = cohere_client
    
    async def summarize_messages(self, messages: List[Tuple[str, str]], conversation_id: str) -> str:
        """Summarize a list of (user_msg, ai_msg) tuples"""
        
        # Format messages for summarization
        formatted_messages = []
        for user_msg, ai_msg in messages:
            formatted_messages.append(f"User: {user_msg}")
            formatted_messages.append(f"Assistant: {ai_msg}")
        
        conversation_text = "\n".join(formatted_messages)
        
        summary_prompt = f"""Riassumi questa conversazione in modo conciso ma completo, mantenendo tutte le informazioni importanti come nomi, decisioni, progetti e dettagli tecnici:

{conversation_text}

RIASSUNTO:"""
        
        try:
            response = await asyncio.to_thread(
                self.client.generate,
                prompt=summary_prompt,
                max_tokens=300,
                temperature=0.1  # Low temperature for consistent summaries
            )
            
            # Extract summary from response
            summary = response.generations[0].text.strip()
            
            logger.info(f"Summarized {len(messages)} messages into {len(summary)} characters")
            return summary
            
        except Exception as e:
            logger.error(f"Failed to summarize conversation: {e}")
            # Fallback: create simple bullet-point summary
            return self._create_fallback_summary(messages)
    
    def _create_fallback_summary(self, messages: List[Tuple[str, str]]) -> str:
        """Create a simple fallback summary if AI summarization fails"""
        key_points = []
        
        for user_msg, ai_msg in messages:
            # Extract potential key information
            if any(word in user_msg.lower() for word in ["chiamo", "nome", "sono", "lavoro"]):
                key_points.append(f"Info personale: {user_msg[:100]}")
            elif any(word in user_msg.lower() for word in ["progetto", "app", "sito"]):
                key_points.append(f"Progetto: {user_msg[:100]}")
            elif "?" in user_msg:
                key_points.append(f"Domanda: {user_msg[:100]}")
        
        return "; ".join(key_points[:5])  # Max 5 key points

class HybridMemoryService:
    """
    Hybrid memory service with intelligent storage tiers and optimization
    """
    
    def __init__(self, config: HybridMemoryConfig):
        self.config = config
        self.cohere_client = None
        self.pinecone_client = None
        self.index = None
        self._initialized = False
        
        # Hybrid system components
        self.recent_buffer: Deque[HybridMemoryItem] = deque(maxlen=config.recent_buffer_size)
        self.classifier = MessageImportanceClassifier()
        self.summarizer = None
        
        # Performance tracking
        self.stats = {
            "total_messages": 0,
            "high_importance": 0,
            "medium_importance": 0,
            "low_importance": 0,
            "summarized_chunks": 0
        }
    
    async def initialize(self) -> None:
        """Initialize the hybrid memory service"""
        if self._initialized:
            return
            
        try:
            # Initialize Cohere client
            self.cohere_client = cohere.ClientV2(api_key=self.config.cohere_api_key)
            self.summarizer = ConversationSummarizer(self.cohere_client)
            
            # Initialize Pinecone
            self.pinecone_client = Pinecone(api_key=self.config.pinecone_api_key)
            self.index = self.pinecone_client.Index(
                name=self.config.pinecone_index_name,
                host=self.config.pinecone_host
            )
            
            # Test connections
            await self._test_connections()
            self._initialized = True
            logger.info("Hybrid memory service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize hybrid memory service: {e}")
            raise
    
    async def _test_connections(self) -> None:
        """Test connections to external services"""
        try:
            # Test Cohere
            test_response = await asyncio.to_thread(
                self.cohere_client.embed,
                texts=["test"],
                model=self.config.embedding_model,
                input_type="search_document"
            )
            
            # Test Pinecone
            stats = await asyncio.to_thread(self.index.describe_index_stats)
            logger.info(f"Hybrid memory: {stats.get('total_vector_count', 0)} vectors in index")
            
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            raise
    
    async def store_conversation_turn(
        self, 
        user_message: str, 
        ai_response: str, 
        conversation_id: str,
        additional_metadata: Dict[str, Any] = None
    ) -> bool:
        """
        Store conversation turn using hybrid strategy
        """
        if not self._initialized:
            await self.initialize()
        
        metadata = additional_metadata or {}
        success_count = 0
        
        # ALWAYS analyze with AI - no pre-filtering
        canonical_facts = await self._extract_canonical_facts(user_message)
        
        # Update stats
        self.stats["total_messages"] += 1
        
        # Create items based on what AI extracted
        if canonical_facts:
            # AI found useful information, store as global memories
            user_items = []
            for fact in canonical_facts:
                # Parse fact to extract category if present
                if '|' in fact:
                    fact_content, category = fact.split('|', 1)
                    category = category.strip()
                else:
                    fact_content = fact
                    category = 'general'
                
                user_item = HybridMemoryItem(
                    content=fact_content,
                    metadata={
                        **metadata, 
                        "role": "user", 
                        "type": "personal_info", 
                        "category": category,
                        "fact_type": fact_content.split(":")[0] if ":" in fact_content else "general"
                    },
                    timestamp=datetime.now(),
                    conversation_id="global",
                    message_type="personal",
                    importance=ImportanceLevel.HIGH,
                    storage_tier=StorageTier.GLOBAL
                )
                user_items.append(user_item)
        else:
            # AI found no relevant information, still create conversation memory
            user_item = HybridMemoryItem(
                content=user_message,
                metadata={**metadata, "role": "user"},
                timestamp=datetime.now(),
                conversation_id=conversation_id,
                message_type="chat",
                importance=ImportanceLevel.MEDIUM
            )
        
        # AI responses are NO LONGER automatically stored - only saved manually by user
        
        # STRATEGY 1: Always add to recent buffer
        if canonical_facts:
            # AI found useful information, add first item to recent buffer for context
            if user_items:
                self.recent_buffer.append(user_items[0])
        else:
            self.recent_buffer.append(user_item)
        # AI responses no longer added to recent buffer automatically
        
        # STRATEGY 2: Storage based on AI analysis results
        if canonical_facts:
            # AI found useful information: always store as permanent global memory
            for user_item in user_items:
                if await self._store_permanent(user_item):
                    success_count += 1
                    logger.info(f"Stored AI-extracted fact: {user_item.content[:50]}...")
        else:
            # AI found no relevant information: store as medium-term conversation memory
            ttl_date = datetime.now() + timedelta(days=self.config.medium_term_ttl_days)
            user_item.storage_tier = StorageTier.MEDIUM_TERM
            user_item.ttl = ttl_date
            if await self._store_with_ttl(user_item):
                success_count += 1
        
        # AI responses are no longer automatically stored
        
        # STRATEGY 4: Summarization when buffer is full
        if len(self.recent_buffer) == self.config.recent_buffer_size:
            await self._maybe_summarize_and_compress(conversation_id)
        
        # Success if we stored at least one item (could be multiple personal facts)
        return success_count >= 1
    
    async def store_ai_response_manually(
        self,
        ai_response: str,
        conversation_id: str,
        user_message: str = "",
        additional_metadata: Dict[str, Any] = None
    ) -> bool:
        """
        Store AI response manually when user decides it's important
        """
        if not self._initialized:
            await self.initialize()
        
        metadata = additional_metadata or {}
        metadata.update({
            "role": "assistant",
            "manually_saved": True,
            "related_user_message": user_message
        })
        
        # Create AI item as regular chat content (not chat_history)
        ai_item = HybridMemoryItem(
            content=ai_response,
            metadata=metadata,
            timestamp=datetime.now(),
            conversation_id=conversation_id,
            message_type="chat",  # Store as regular chat content
            importance=ImportanceLevel.HIGH,  # User-selected = important
            storage_tier=StorageTier.IMPORTANT
        )
        
        # Store permanently
        success = await self._store_permanent(ai_item)
        
        if success:
            logger.info(f"Manually stored AI response: {ai_response[:50]}...")
        
        return success
    
    async def _store_permanent(self, item: HybridMemoryItem) -> bool:
        """Store item permanently in Pinecone"""
        try:
            embedding = await self._create_embedding(item.content)
            memory_id = self._generate_memory_id(item.content, item.conversation_id, item.storage_tier.value)
            
            # Filter out None values to avoid Pinecone errors
            filtered_metadata = {k: v for k, v in item.metadata.items() if v is not None}
            
            metadata = {
                "content": item.content,
                "timestamp": item.timestamp.isoformat(),
                "conversation_id": item.conversation_id,
                "message_type": item.message_type,
                "importance": item.importance.value,
                "storage_tier": item.storage_tier.value,
                **filtered_metadata
            }
            
            await asyncio.to_thread(
                self.index.upsert,
                vectors=[{
                    "id": memory_id,
                    "values": embedding,
                    "metadata": metadata
                }]
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to store permanent memory: {e}")
            return False
    
    async def _store_with_ttl(self, item: HybridMemoryItem) -> bool:
        """Store item with TTL (time-to-live)"""
        try:
            embedding = await self._create_embedding(item.content)
            memory_id = self._generate_memory_id(item.content, item.conversation_id, item.storage_tier.value)
            
            # Filter out None values to avoid Pinecone errors
            filtered_metadata = {k: v for k, v in item.metadata.items() if v is not None}
            
            metadata = {
                "content": item.content,
                "timestamp": item.timestamp.isoformat(),
                "conversation_id": item.conversation_id,
                "message_type": item.message_type,
                "importance": item.importance.value,
                "storage_tier": item.storage_tier.value,
                **filtered_metadata
            }
            
            # Add TTL if present
            if item.ttl:
                metadata["ttl"] = item.ttl.isoformat()
            
            await asyncio.to_thread(
                self.index.upsert,
                vectors=[{
                    "id": memory_id,
                    "values": embedding,
                    "metadata": metadata
                }]
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to store TTL memory: {e}")
            return False
    
    async def _maybe_summarize_and_compress(self, conversation_id: str):
        """Summarize recent buffer when full and store as compressed memory"""
        try:
            # Extract conversation turns from recent buffer for this conversation
            conv_messages = []
            for item in list(self.recent_buffer):
                if item.conversation_id == conversation_id and item.metadata.get("role") == "user":
                    # Find corresponding AI response
                    ai_response = None
                    for next_item in list(self.recent_buffer):
                        if (next_item.conversation_id == conversation_id and 
                            next_item.metadata.get("role") == "assistant" and
                            next_item.timestamp > item.timestamp):
                            ai_response = next_item.content
                            break
                    
                    if ai_response:
                        conv_messages.append((item.content, ai_response))
            
            if len(conv_messages) >= 5:  # Only summarize if enough content
                summary = await self.summarizer.summarize_messages(conv_messages, conversation_id)
                
                # Store summary as compressed memory
                summary_item = HybridMemoryItem(
                    content=summary,
                    metadata={"type": "conversation_summary", "original_turns": len(conv_messages)},
                    timestamp=datetime.now(),
                    conversation_id=conversation_id,
                    message_type="summary",
                    importance=ImportanceLevel.MEDIUM,
                    storage_tier=StorageTier.COMPRESSED
                )
                
                await self._store_permanent(summary_item)
                self.stats["summarized_chunks"] += 1
                
                logger.info(f"Summarized {len(conv_messages)} conversation turns for {conversation_id}")
            
        except Exception as e:
            logger.error(f"Failed to summarize and compress: {e}")
    
    def _contains_personal_info(self, message: str) -> bool:
        """Check if message contains personal information worth storing globally using rule-based patterns"""
        message_lower = message.lower().strip()
        
        # Skip questions - they are not personal facts
        if any(q in message_lower for q in ["come mi chiamo", "qual è il mio nome", "chi sono", "come sono", "cosa faccio"]):
            return False
        
        # Skip generic questions
        if message_lower.endswith("?") and any(w in message_lower[:10] for w in ["come", "cosa", "quando", "dove", "perché", "chi"]):
            return False
        
        # Patterns that indicate personal information (statements, not questions)
        personal_patterns = [
            # Basic personal info
            "mi chiamo", "il mio nome è", "nome è",  
            "lavoro come", "lavoro in", "sono un", "sono una",
            "faccio il", "faccio la", "studio", "abito a", "vivo a",
            "ho anni", "ho 1", "ho 2", "ho 3", "sono nato", "vengo da",
            
            # Preferences and interests
            "mi piace", "preferisco", "amo", "odio", "detesto",
            "sono bravo in", "mi occupo di", "mia passione", "mio hobby",
            
            # Health and medical
            "ho l'", "ho il", "ho la", "soffro di", "sono allergico",
            "ho problemi di", "ho disturbi", "prendo farmaci", "sono in terapia",
            "ho ansia", "sono ansioso", "sono depresso", "ho dolori",
            "non posso mangiare", "sono intollerante", "ho malattie",
            
            # Physical characteristics
            "sono alto", "sono alta", "peso", "misuro", "ho i capelli",
            "ho gli occhi", "porto gli occhiali", "sono magro", "sono grasso",
            "faccio sport", "vado in palestra", "corro", "nuoto"
        ]
        
        return any(pattern in message_lower for pattern in personal_patterns)
    
    async def _extract_canonical_facts(self, message: str) -> List[str]:
        """Use AI to extract canonical facts from any user message - ALWAYS calls AI"""
        
        # NO PRE-FILTERS - Always call AI to analyze every input
        
        # Single AI call that does both evaluation and extraction with categorization - MULTILINGUAL
        extraction_prompt = f"""Analyze the following user message and extract ONLY relevant personal information in structured format with categories. The input message can be in any language.

Message: "{message}"

EXTRACT information using these EXACT formats (one per line):
- user_name: [person's name] | category:personal
- user_age: [age in numbers] | category:personal
- user_location: [city, country, region where they live] | category:personal
- user_job: [profession, work, occupation] | category:work
- user_likes: [what they like, hobbies, passions, interests - one per line] | category:hobby
- user_dislikes: [what they don't like, hate] | category:hobby
- user_condition: [medical conditions, psychological states, disorders] | category:health
- user_skill: [competencies, abilities, things they're good at] | category:work
- user_goal: [objectives, aspirations, future desires] | category:goals
- user_experience: [significant experiences, background] | category:personal
- user_relationship: [marital status, family relationships] | category:relationships
- user_preference: [specific preferences, personal choices] | category:personal

AVAILABLE CATEGORIES:
- personal: Basic personal info (name, age, location, preferences)
- work: Professional info (job, skills, work experience)
- hobby: Interests and recreational activities (likes, dislikes, hobbies)
- health: Medical and psychological conditions
- relationships: Family, romantic, social relationships
- goals: Future aspirations, objectives, plans

CRITICAL RULES:
1. Extract ONLY information explicitly mentioned in the message
2. DO NOT invent or deduce information that is not present
3. If there is NO personal information, respond: "NO_INFORMATION"
4. Use EXACTLY the format: type:value | category:category_name
5. For multiple elements of the same type, use separate lines
6. Always assign the most appropriate category from the list above
7. DO NOT add explanations, comments or extra text

EXAMPLES:
Input: "Mi chiamo Sara e ho 25 anni, vivo a Milano"
Output: 
user_name:Sara | category:personal
user_age:25 | category:personal
user_location:Milano | category:personal

Input: "I work as a software engineer and I love programming"
Output:
user_job:software engineer | category:work
user_likes:programming | category:hobby

Input: "Je suis anxieux et j'ai des TOC, j'aimerais devenir médecin"
Output:
user_condition:anxiety | category:health
user_condition:OCD | category:health
user_goal:become doctor | category:goals

Input: "What's the weather today?"
Output: NO_INFORMATION"""

        try:
            # Import the call_model_once function
            from main import call_model_once
            
            response = await call_model_once([
                {"role": "user", "content": extraction_prompt}
            ], temperature=0.1)  # Low temperature for consistent extraction
            
            # Parse the AI response with categories
            facts = []
            if response and "NO_INFORMATION" not in response:
                lines = response.strip().split('\n')
                for line in lines:
                    line = line.strip()
                    if ':' in line and '|' in line and not line.startswith('#') and not line.startswith('-') and not line.startswith('*'):
                        # Parse format: type:value | category:category_name
                        try:
                            main_part, category_part = line.split('|', 1)
                            main_part = main_part.strip()
                            category_part = category_part.strip()
                            
                            if ':' in main_part and main_part.count(':') == 1:
                                fact_type, fact_value = main_part.split(':', 1)
                                fact_type = fact_type.strip()
                                fact_value = fact_value.strip()
                                
                                # Extract category
                                category = "general"  # default
                                if category_part.startswith('category:'):
                                    category = category_part.split(':', 1)[1].strip()
                                
                                # Validate that it's a recognized fact type
                                valid_types = [
                                    'user_name', 'user_age', 'user_location', 'user_job',
                                    'user_likes', 'user_dislikes', 'user_condition', 
                                    'user_skill', 'user_goal', 'user_experience',
                                    'user_relationship', 'user_preference'
                                ]
                                
                                # Validate category
                                valid_categories = ['personal', 'work', 'hobby', 'health', 'relationships', 'goals']
                                if category not in valid_categories:
                                    category = 'general'
                                
                                if fact_type in valid_types and fact_value:
                                    facts.append(f"{fact_type}:{fact_value}|{category}")
                        except ValueError:
                            # If parsing fails, skip this line
                            continue
            
            logger.info(f"AI extracted {len(facts)} facts from message: {message[:50]}...")
            if facts:
                logger.info(f"Extracted facts: {facts}")
            return facts
            
        except Exception as e:
            logger.error(f"Error in AI fact extraction: {e}")
            # Fallback: return empty list if AI extraction fails
            return []
    
    async def _create_embedding(self, text: str) -> List[float]:
        """Create embedding using Cohere"""
        if not self._initialized:
            await self.initialize()
            
        try:
            response = await asyncio.to_thread(
                self.cohere_client.embed,
                texts=[text],
                model=self.config.embedding_model,
                input_type="search_document"
            )
            
            if hasattr(response.embeddings, 'float_'):
                embeddings_list = response.embeddings.float_
            else:
                raise Exception(f"Unknown embeddings format: {type(response.embeddings)}")
            
            if not embeddings_list or len(embeddings_list) == 0:
                raise Exception("Empty embeddings list")
                
            return embeddings_list[0]
            
        except Exception as e:
            logger.error(f"Failed to create embedding: {e}")
            raise
    
    def _generate_memory_id(self, content: str, conversation_id: str, tier: str) -> str:
        """Generate unique ID for memory item"""
        base_string = f"{content}_{conversation_id}_{tier}_{datetime.now().isoformat()}"
        return hashlib.md5(base_string.encode()).hexdigest()
    
    async def retrieve_memories(
        self,
        query: str,
        conversation_id: Optional[str] = None,
        limit: int = 20,
        include_recent: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Retrieve memories using hybrid strategy:
        1. Recent buffer (immediate context)
        2. Permanent storage (semantic search)
        """
        if not self._initialized:
            await self.initialize()
        
        all_memories = []
        
        # STRATEGY 1: Search recent buffer first
        if include_recent:
            recent_memories = self._search_recent_buffer(query, conversation_id)
            all_memories.extend(recent_memories)
        
        # STRATEGY 2: Search permanent storage
        try:
            query_embedding = await self._create_embedding(query)
            
            # Build filter for permanent storage
            filter_conditions = {}
            if conversation_id:
                filter_conditions["conversation_id"] = {"$in": [conversation_id, "global"]}
            
            # Optimize query with sparse vector support and better filtering
            query_params = {
                "vector": query_embedding,
                "top_k": min(limit * 2, 100),  # Cap at 100 for better recall
                "include_metadata": True,
            }
            
            # Only add filter if we have conditions to avoid empty filter issues
            if filter_conditions:
                query_params["filter"] = filter_conditions
            
            response = await asyncio.to_thread(self.index.query, **query_params)
            
            for match in response.matches:
                if match.score >= self.config.similarity_threshold:
                    # Check TTL expiration
                    ttl_str = match.metadata.get("ttl")
                    if ttl_str:
                        ttl_date = datetime.fromisoformat(ttl_str)
                        if datetime.now() > ttl_date:
                            continue  # Skip expired memories
                    
                    # FILTER TEST DATA - Skip ONLY explicit dummy/test data
                    metadata = match.metadata
                    conversation_id = metadata.get("conversation_id", "")
                    if (metadata.get("test") == True or 
                        metadata.get("test") == "true" or
                        # More specific test filtering - avoid false positives
                        conversation_id in ["test", "test_data", "dummy", "example"] or
                        conversation_id.startswith("test-") or
                        conversation_id.startswith("dummy-")):
                        logger.debug(f"Skipping test data: {metadata}")
                        continue
                    
                    all_memories.append({
                        "id": match.id,
                        "content": match.metadata.get("content", ""),
                        "score": float(match.score),
                        "timestamp": match.metadata.get("timestamp"),
                        "conversation_id": match.metadata.get("conversation_id"),
                        "message_type": match.metadata.get("message_type", "chat"),
                        "importance": match.metadata.get("importance", "low"),
                        "storage_tier": match.metadata.get("storage_tier", "unknown"),
                        "source": "permanent",
                        "metadata": {k: v for k, v in match.metadata.items() 
                                   if k not in ["content", "timestamp", "conversation_id", "message_type"]}
                    })
            
        except Exception as e:
            logger.error(f"Failed to search permanent storage: {e}")
        
        # Sort by relevance score and importance, limit results
        all_memories.sort(key=lambda x: (x.get("score", 0), 
                                       1 if x.get("importance") == "high" else 0.5 if x.get("importance") == "medium" else 0), 
                         reverse=True)
        
        logger.info(f"Retrieved {len(all_memories[:limit])} hybrid memories for query: {query[:50]}...")
        return all_memories[:limit]
    
    def _search_recent_buffer(self, query: str, conversation_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search recent buffer using simple text matching"""
        query_lower = query.lower()
        results = []
        
        for item in reversed(list(self.recent_buffer)):  # Most recent first
            if conversation_id and item.conversation_id != conversation_id:
                continue
                
            # Simple relevance scoring based on word overlap
            content_lower = item.content.lower()
            query_words = set(query_lower.split())
            content_words = set(content_lower.split())
            
            overlap = len(query_words.intersection(content_words))
            if overlap > 0:
                # FILTER TEST DATA - Skip ONLY explicit dummy/test data from recent buffer
                metadata = item.metadata
                conversation_id = item.conversation_id
                if (metadata.get("test") == True or 
                    metadata.get("test") == "true" or
                    # More specific test filtering - avoid false positives
                    conversation_id in ["test", "test_data", "dummy", "example"] or
                    conversation_id.startswith("test-") or
                    conversation_id.startswith("dummy-")):
                    continue
                
                relevance_score = overlap / len(query_words)
                
                results.append({
                    "content": item.content,
                    "score": relevance_score,
                    "timestamp": item.timestamp.isoformat(),
                    "conversation_id": item.conversation_id,
                    "message_type": item.message_type,
                    "importance": item.importance.value,
                    "storage_tier": "recent_buffer",
                    "source": "recent",
                    "metadata": item.metadata
                })
        
        return results
    
    async def get_conversation_context(
        self, 
        current_message: str, 
        conversation_id: str, 
        context_limit: int = 15
    ) -> str:
        """Get conversation context using hybrid approach"""
        memories = await self.retrieve_memories(
            query=current_message,
            conversation_id=conversation_id,
            limit=context_limit,
            include_recent=True
        )
        
        if not memories:
            return ""
        
        context_parts = ["## Contesto dalla memoria:"]
        
        for memory in memories:
            timestamp = memory.get("timestamp", "")
            role = memory.get("metadata", {}).get("role", "unknown")
            content = memory.get("content", "")
            source = memory.get("source", "unknown")
            importance = memory.get("importance", "low")
            
            # Add source indicator for debugging
            source_icon = "🔄" if source == "recent" else "💾"
            importance_icon = "🔥" if importance == "high" else "⭐" if importance == "medium" else ""
            
            context_parts.append(f"**{role.title()}** {source_icon}{importance_icon} ({timestamp[:19]}): {content}")
        
        return "\n".join(context_parts)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get hybrid memory system statistics"""
        return {
            **self.stats,
            "recent_buffer_size": len(self.recent_buffer),
            "recent_buffer_max": self.config.recent_buffer_size
        }

# Global hybrid memory service instance
_hybrid_memory_service: Optional[HybridMemoryService] = None

def get_hybrid_memory_service() -> Optional[HybridMemoryService]:
    """Get the global hybrid memory service instance"""
    return _hybrid_memory_service

async def initialize_hybrid_memory_service() -> HybridMemoryService:
    """Initialize and return the global hybrid memory service"""
    global _hybrid_memory_service
    
    if _hybrid_memory_service is None:
        config = HybridMemoryConfig(
            cohere_api_key=os.getenv("COHERE_API_KEY", ""),
            pinecone_api_key=os.getenv("PINECONE_API_KEY", ""),
            pinecone_index_name=os.getenv("PINECONE_INDEX", "chatbot-cli-map"),
            pinecone_host=os.getenv("PINECONE_HOST", "https://chatbot-cli-map-mp69iv8.svc.aped-4627-b74a.pinecone.io")
        )
        
        if not config.cohere_api_key or not config.pinecone_api_key:
            logger.warning("Hybrid memory service API keys not configured")
            return None
            
        _hybrid_memory_service = HybridMemoryService(config)
        await _hybrid_memory_service.initialize()
    
    return _hybrid_memory_service