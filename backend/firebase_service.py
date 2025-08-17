"""
Firebase Service for Backend Integration
Handles Firestore operations for concept maps and user data
"""

import os
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import asyncio

try:
    import firebase_admin
    from firebase_admin import credentials, firestore
    FIREBASE_AVAILABLE = True
except ImportError:
    FIREBASE_AVAILABLE = False
    firebase_admin = None
    credentials = None
    firestore = None

logger = logging.getLogger(__name__)

class FirebaseService:
    """Service for Firebase Firestore operations"""
    
    def __init__(self):
        self.db = None
        self._initialized = False
        
    async def initialize(self) -> bool:
        """Initialize Firebase Admin SDK"""
        if not FIREBASE_AVAILABLE:
            logger.warning("Firebase Admin SDK not available - install with: pip install firebase-admin")
            return False
            
        if self._initialized:
            return True
            
        try:
            # Initialize Firebase Admin SDK
            # For development, you can use a service account key file
            # For production, use environment variables or Cloud Run automatic auth
            
            firebase_config = {
                "type": "service_account",
                "project_id": "chat-cli-map",
                "private_key_id": os.getenv("FIREBASE_PRIVATE_KEY_ID"),
                "private_key": os.getenv("FIREBASE_PRIVATE_KEY", "").replace('\\n', '\n'),
                "client_email": os.getenv("FIREBASE_CLIENT_EMAIL"),
                "client_id": os.getenv("FIREBASE_CLIENT_ID"),
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "client_x509_cert_url": os.getenv("FIREBASE_CLIENT_CERT_URL")
            }
            
            # Check if all required fields are present
            required_fields = ["project_id", "private_key", "client_email"]
            missing_fields = [field for field in required_fields if not firebase_config.get(field)]
            
            if missing_fields:
                logger.warning(f"Missing Firebase config fields: {missing_fields}. Using mock mode.")
                self.db = MockFirestore()
                self._initialized = True
                return True
            
            # Initialize Firebase app if not already initialized
            if not firebase_admin._apps:
                cred = credentials.Certificate(firebase_config)
                firebase_admin.initialize_app(cred)
            
            # Get Firestore client
            self.db = firestore.client()
            self._initialized = True
            
            logger.info("Firebase service initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Firebase: {e}")
            # Fallback to mock for development
            self.db = MockFirestore()
            self._initialized = True
            return True
    
    async def store_concept_map(self, user_id: str, concept_map_data: Dict[str, Any]) -> str:
        """Store a concept map in Firestore"""
        if not self._initialized:
            await self.initialize()
            
        try:
            # Add metadata
            concept_map_data.update({
                "userId": user_id,
                "createdAt": datetime.now(),
                "updatedAt": datetime.now()
            })
            
            # Store in Firestore
            doc_ref = self.db.collection('concept_maps').add(concept_map_data)
            concept_map_id = doc_ref[1].id if isinstance(doc_ref, tuple) else doc_ref.id
            
            logger.info(f"Stored concept map {concept_map_id} for user {user_id}")
            return concept_map_id
            
        except Exception as e:
            logger.error(f"Failed to store concept map: {e}")
            raise
    
    async def get_user_concept_maps(self, user_id: str) -> List[tuple]:
        """Get all concept maps for a user in the format expected by concept_map_analyzer"""
        if not self._initialized:
            await self.initialize()
            
        try:
            maps_ref = self.db.collection('concept_maps').where('userId', '==', user_id)
            docs = maps_ref.stream()
            
            concept_maps = []
            for doc in docs:
                map_data = doc.to_dict()
                # Return tuple format: (map_id, map_data)
                concept_maps.append((doc.id, map_data))
            
            logger.info(f"Retrieved {len(concept_maps)} concept maps for user {user_id}")
            return concept_maps
            
        except Exception as e:
            logger.error(f"Failed to retrieve concept maps: {e}")
            return []
    
    async def update_concept_map(self, map_id: str, user_id: str, concept_map_data: Dict[str, Any]) -> bool:
        """Update an existing concept map"""
        if not self._initialized:
            await self.initialize()
            
        try:
            # Verify ownership
            doc_ref = self.db.collection('concept_maps').document(map_id)
            doc = doc_ref.get()
            
            if not doc.exists:
                logger.warning(f"Concept map {map_id} not found")
                return False
                
            existing_data = doc.to_dict()
            if existing_data.get('userId') != user_id:
                logger.warning(f"User {user_id} does not own concept map {map_id}")
                return False
            
            # Update data
            concept_map_data.update({
                "updatedAt": datetime.now()
            })
            
            doc_ref.update(concept_map_data)
            logger.info(f"Updated concept map {map_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update concept map: {e}")
            return False
    
    async def delete_concept_map(self, map_id: str, user_id: str) -> bool:
        """Delete a concept map"""
        if not self._initialized:
            await self.initialize()
            
        try:
            # Verify ownership
            doc_ref = self.db.collection('concept_maps').document(map_id)
            doc = doc_ref.get()
            
            if not doc.exists:
                return False
                
            existing_data = doc.to_dict()
            if existing_data.get('userId') != user_id:
                return False
            
            doc_ref.delete()
            logger.info(f"Deleted concept map {map_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete concept map: {e}")
            return False
    
    async def store_user_profile(self, user_id: str, profile_data: Dict[str, Any]) -> bool:
        """Store user profile data"""
        if not self._initialized:
            await self.initialize()
            
        try:
            profile_data.update({
                "userId": user_id,
                "updatedAt": datetime.now()
            })
            
            self.db.collection('user_profiles').document(user_id).set(profile_data, merge=True)
            logger.info(f"Stored user profile for {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store user profile: {e}")
            return False
    
    async def get_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user profile data"""
        if not self._initialized:
            await self.initialize()
            
        try:
            doc_ref = self.db.collection('user_profiles').document(user_id)
            doc = doc_ref.get()
            
            if doc.exists:
                return doc.to_dict()
            return None
            
        except Exception as e:
            logger.error(f"Failed to get user profile: {e}")
            return None

class MockFirestore:
    """Mock Firestore for development without Firebase credentials"""
    
    def __init__(self):
        self.data = {
            'concept_maps': {},
            'user_profiles': {}
        }
        self.next_id = 1
        
    def collection(self, collection_name: str):
        return MockCollection(self, collection_name)

class MockCollection:
    def __init__(self, firestore: MockFirestore, collection_name: str):
        self.firestore = firestore
        self.collection_name = collection_name
        
    def add(self, data: Dict[str, Any]):
        doc_id = f"mock_{self.firestore.next_id}"
        self.firestore.next_id += 1
        
        if self.collection_name not in self.firestore.data:
            self.firestore.data[self.collection_name] = {}
            
        self.firestore.data[self.collection_name][doc_id] = data
        
        # Return a mock document reference
        return MockDocRef(doc_id), MockDocRef(doc_id)
    
    def document(self, doc_id: str):
        return MockDocRef(doc_id, self.firestore, self.collection_name)
    
    def where(self, field: str, op: str, value: Any):
        return MockQuery(self.firestore, self.collection_name, field, op, value)

class MockDocRef:
    def __init__(self, doc_id: str, firestore: MockFirestore = None, collection_name: str = None):
        self.id = doc_id
        self.firestore = firestore
        self.collection_name = collection_name
    
    def get(self):
        if self.firestore and self.collection_name:
            data = self.firestore.data.get(self.collection_name, {}).get(self.id)
            return MockDoc(self.id, data)
        return MockDoc(self.id, None)
    
    def set(self, data: Dict[str, Any], merge: bool = False):
        if self.firestore and self.collection_name:
            if self.collection_name not in self.firestore.data:
                self.firestore.data[self.collection_name] = {}
            self.firestore.data[self.collection_name][self.id] = data
    
    def update(self, data: Dict[str, Any]):
        if self.firestore and self.collection_name:
            existing = self.firestore.data.get(self.collection_name, {}).get(self.id, {})
            existing.update(data)
            self.firestore.data[self.collection_name][self.id] = existing
    
    def delete(self):
        if self.firestore and self.collection_name:
            self.firestore.data.get(self.collection_name, {}).pop(self.id, None)

class MockDoc:
    def __init__(self, doc_id: str, data: Optional[Dict[str, Any]]):
        self.id = doc_id
        self.data = data
    
    @property
    def exists(self):
        return self.data is not None
    
    def to_dict(self):
        return self.data or {}

class MockQuery:
    def __init__(self, firestore: MockFirestore, collection_name: str, field: str, op: str, value: Any):
        self.firestore = firestore
        self.collection_name = collection_name
        self.field = field
        self.op = op
        self.value = value
    
    def stream(self):
        collection_data = self.firestore.data.get(self.collection_name, {})
        results = []
        
        for doc_id, data in collection_data.items():
            if self.op == '==' and data.get(self.field) == self.value:
                results.append(MockDoc(doc_id, data))
                
        return results

# Global Firebase service instance
_firebase_service: Optional[FirebaseService] = None

async def get_firebase_service() -> Optional[FirebaseService]:
    """Get or initialize the Firebase service"""
    global _firebase_service
    
    if _firebase_service is None:
        _firebase_service = FirebaseService()
        success = await _firebase_service.initialize()
        if not success:
            logger.warning("Firebase service initialization failed")
            return None
    
    return _firebase_service