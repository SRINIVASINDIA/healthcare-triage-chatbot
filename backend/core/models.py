"""
Data models for conversation sessions and messages
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum
from decimal import Decimal


class ConversationState(Enum):
    INITIAL = "INITIAL"
    GATHERING_INFO = "GATHERING_INFO"
    READY_FOR_TRIAGE = "READY_FOR_TRIAGE"
    COMPLETED = "COMPLETED"


class MessageRole(Enum):
    USER = "user"
    ASSISTANT = "assistant"


@dataclass
class MedicalEntity:
    type: str
    text: str
    score: float
    category: Optional[str] = None


@dataclass
class Message:
    timestamp: str
    role: MessageRole
    content: str
    extracted_entities: List[MedicalEntity] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        """Convert Message to dictionary format for DynamoDB storage"""
        return {
            "timestamp": self.timestamp,
            "role": self.role.value,
            "content": self.content,
            "extractedEntities": [
                {
                    "type": entity.type,
                    "text": entity.text,
                    "score": Decimal(str(entity.score)),  # Convert float to Decimal for DynamoDB
                    "category": entity.category
                }
                for entity in self.extracted_entities
            ]
        }


@dataclass
class ConversationSession:
    session_id: str
    created_at: str
    last_updated_at: str
    ttl: int
    conversation_state: ConversationState
    message_history: List[Message]
    aggregated_entities: Dict[str, List[str]]
    follow_up_count: int = 0
    emergency_detected: bool = False
    
    def to_dynamodb_item(self) -> Dict:
        """Convert ConversationSession to DynamoDB item format"""
        return {
            "sessionId": self.session_id,
            "createdAt": self.created_at,
            "lastUpdatedAt": self.last_updated_at,
            "ttl": self.ttl,
            "conversationState": self.conversation_state.value,
            "messageHistory": [msg.to_dict() for msg in self.message_history],
            "aggregatedEntities": self.aggregated_entities,
            "followUpCount": self.follow_up_count,
            "emergencyDetected": self.emergency_detected
        }
    
    @classmethod
    def from_dynamodb_item(cls, item: Dict) -> 'ConversationSession':
        """Create ConversationSession from DynamoDB item"""
        # Parse messages from DynamoDB format
        messages = [
            Message(
                timestamp=msg["timestamp"],
                role=MessageRole(msg["role"]),
                content=msg["content"],
                extracted_entities=[
                    MedicalEntity(
                        type=entity["type"],
                        text=entity["text"],
                        score=float(entity["score"]),  # Convert Decimal back to float
                        category=entity.get("category")
                    )
                    for entity in msg.get("extractedEntities", [])
                ]
            )
            for msg in item.get("messageHistory", [])
        ]
        
        return cls(
            session_id=item["sessionId"],
            created_at=item["createdAt"],
            last_updated_at=item["lastUpdatedAt"],
            ttl=item["ttl"],
            conversation_state=ConversationState(item["conversationState"]),
            message_history=messages,
            aggregated_entities=item.get("aggregatedEntities", {}),
            follow_up_count=item.get("followUpCount", 0),
            emergency_detected=item.get("emergencyDetected", False)
        )
