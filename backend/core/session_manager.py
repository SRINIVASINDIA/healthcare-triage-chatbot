"""
Session Manager for DynamoDB operations
Handles creation, retrieval, and updates of conversation sessions
"""

import boto3
import uuid
import time
from datetime import datetime, timezone
from typing import Optional
from botocore.exceptions import ClientError
from .models import ConversationSession, ConversationState, Message, MessageRole


class SessionManager:
    def __init__(self, table_name: str):
        self.table_name = table_name
        self.dynamodb = boto3.resource('dynamodb')
        self.table = self.dynamodb.Table(table_name)
        self.max_messages = 50
        self.ttl_hours = 24
        self.max_retries = 3
        self.base_retry_delay = 0.1  # 100ms
    
    def create_session(self, session_id: Optional[str] = None) -> ConversationSession:
        """Create a new conversation session"""
        if session_id is None:
            session_id = str(uuid.uuid4())
        
        now = datetime.now(timezone.utc).isoformat()
        ttl = int(time.time()) + (self.ttl_hours * 3600)
        
        session = ConversationSession(
            session_id=session_id,
            created_at=now,
            last_updated_at=now,
            ttl=ttl,
            conversation_state=ConversationState.INITIAL,
            message_history=[],
            aggregated_entities={
                "symptoms": [],
                "anatomy": [],
                "medications": [],
                "conditions": [],
                "timeExpressions": []
            },
            follow_up_count=0,
            emergency_detected=False
        )
        
        # Store in DynamoDB with retry logic
        self._put_item_with_retry(session.to_dynamodb_item())
        
        return session
    
    def get_session(self, session_id: str) -> Optional[ConversationSession]:
        """Retrieve an existing session"""
        try:
            response = self._get_item_with_retry(session_id)
            
            if 'Item' not in response:
                return None
            
            return ConversationSession.from_dynamodb_item(response['Item'])
        
        except Exception as e:
            print(f"Error retrieving session {session_id}: {str(e)}")
            return None
    
    def update_session(self, session: ConversationSession) -> bool:
        """Update session in DynamoDB"""
        try:
            # Update timestamp and TTL
            session.last_updated_at = datetime.now(timezone.utc).isoformat()
            session.ttl = int(time.time()) + (self.ttl_hours * 3600)
            
            # Store with retry logic
            self._put_item_with_retry(session.to_dynamodb_item())
            
            return True
        
        except Exception as e:
            print(f"Error updating session {session.session_id}: {str(e)}")
            return False
    
    def append_message(self, session_id: str, message: Message) -> bool:
        """Append a message to session history with 50-message limit enforcement"""
        try:
            session = self.get_session(session_id)
            
            if session is None:
                print(f"Session {session_id} not found")
                return False
            
            # Append the new message
            session.message_history.append(message)
            
            # Enforce 50-message limit by removing oldest messages
            if len(session.message_history) > self.max_messages:
                # Remove oldest messages to stay at limit
                session.message_history = session.message_history[-self.max_messages:]
            
            # Update aggregated entities if message has extracted entities
            if message.extracted_entities:
                for entity in message.extracted_entities:
                    entity_type_map = {
                        "SYMPTOM": "symptoms",
                        "ANATOMY": "anatomy",
                        "MEDICATION": "medications",
                        "MEDICAL_CONDITION": "conditions",
                        "TIME_EXPRESSION": "timeExpressions"
                    }
                    
                    key = entity_type_map.get(entity.type)
                    if key and entity.text not in session.aggregated_entities.get(key, []):
                        if key not in session.aggregated_entities:
                            session.aggregated_entities[key] = []
                        session.aggregated_entities[key].append(entity.text)
            
            # Update the session
            return self.update_session(session)
        
        except Exception as e:
            print(f"Error appending message to session {session_id}: {str(e)}")
            return False
    
    def update_ttl(self, session_id: str) -> bool:
        """Reset TTL to 24 hours"""
        try:
            session = self.get_session(session_id)
            
            if session is None:
                print(f"Session {session_id} not found")
                return False
            
            # Update TTL and timestamp
            session.ttl = int(time.time()) + (self.ttl_hours * 3600)
            session.last_updated_at = datetime.now(timezone.utc).isoformat()
            
            # Update in DynamoDB
            return self.update_session(session)
        
        except Exception as e:
            print(f"Error updating TTL for session {session_id}: {str(e)}")
            return False
    
    def _put_item_with_retry(self, item: dict) -> None:
        """Put item to DynamoDB with exponential backoff retry logic"""
        for attempt in range(self.max_retries):
            try:
                self.table.put_item(Item=item)
                return
            
            except ClientError as e:
                error_code = e.response['Error']['Code']
                
                # Retry on throttling or service errors
                if error_code in ['ProvisionedThroughputExceededException', 
                                 'ThrottlingException', 
                                 'ServiceUnavailable',
                                 'InternalServerError']:
                    
                    if attempt < self.max_retries - 1:
                        # Exponential backoff: 100ms, 200ms, 400ms
                        delay = self.base_retry_delay * (2 ** attempt)
                        time.sleep(delay)
                        continue
                
                # Re-raise if not retryable or max retries exceeded
                raise
    
    def _get_item_with_retry(self, session_id: str) -> dict:
        """Get item from DynamoDB with exponential backoff retry logic"""
        for attempt in range(self.max_retries):
            try:
                return self.table.get_item(
                    Key={'sessionId': session_id},
                    ConsistentRead=True  # Use consistent reads as per requirement 7.7
                )
            
            except ClientError as e:
                error_code = e.response['Error']['Code']
                
                # Retry on throttling or service errors
                if error_code in ['ProvisionedThroughputExceededException', 
                                 'ThrottlingException', 
                                 'ServiceUnavailable',
                                 'InternalServerError']:
                    
                    if attempt < self.max_retries - 1:
                        # Exponential backoff: 100ms, 200ms, 400ms
                        delay = self.base_retry_delay * (2 ** attempt)
                        time.sleep(delay)
                        continue
                
                # Re-raise if not retryable or max retries exceeded
                raise
