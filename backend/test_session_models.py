"""
Basic tests for data models and session management
"""

import pytest
from datetime import datetime, timezone
from core.models import (
    ConversationSession, Message, MedicalEntity,
    ConversationState, MessageRole
)


def test_medical_entity_creation():
    """Test MedicalEntity dataclass creation"""
    entity = MedicalEntity(
        type="SYMPTOM",
        text="headache",
        score=0.95,
        category="SIGN_OR_SYMPTOM"
    )
    
    assert entity.type == "SYMPTOM"
    assert entity.text == "headache"
    assert entity.score == 0.95
    assert entity.category == "SIGN_OR_SYMPTOM"


def test_message_to_dict():
    """Test Message serialization to dictionary"""
    entity = MedicalEntity(
        type="SYMPTOM",
        text="fever",
        score=0.98,
        category=None
    )
    
    message = Message(
        timestamp="2024-01-15T10:30:00Z",
        role=MessageRole.USER,
        content="I have a fever",
        extracted_entities=[entity]
    )
    
    msg_dict = message.to_dict()
    
    assert msg_dict["timestamp"] == "2024-01-15T10:30:00Z"
    assert msg_dict["role"] == "user"
    assert msg_dict["content"] == "I have a fever"
    assert len(msg_dict["extractedEntities"]) == 1
    assert msg_dict["extractedEntities"][0]["type"] == "SYMPTOM"
    assert msg_dict["extractedEntities"][0]["text"] == "fever"


def test_conversation_session_to_dynamodb_item():
    """Test ConversationSession serialization to DynamoDB format"""
    message = Message(
        timestamp="2024-01-15T10:30:00Z",
        role=MessageRole.USER,
        content="I have a headache",
        extracted_entities=[]
    )
    
    session = ConversationSession(
        session_id="test-session-123",
        created_at="2024-01-15T10:00:00Z",
        last_updated_at="2024-01-15T10:30:00Z",
        ttl=1705320000,
        conversation_state=ConversationState.GATHERING_INFO,
        message_history=[message],
        aggregated_entities={"symptoms": ["headache"]},
        follow_up_count=1,
        emergency_detected=False
    )
    
    item = session.to_dynamodb_item()
    
    assert item["sessionId"] == "test-session-123"
    assert item["conversationState"] == "GATHERING_INFO"
    assert len(item["messageHistory"]) == 1
    assert item["followUpCount"] == 1
    assert item["emergencyDetected"] is False


def test_conversation_session_from_dynamodb_item():
    """Test ConversationSession deserialization from DynamoDB format"""
    dynamodb_item = {
        "sessionId": "test-session-456",
        "createdAt": "2024-01-15T10:00:00Z",
        "lastUpdatedAt": "2024-01-15T10:30:00Z",
        "ttl": 1705320000,
        "conversationState": "INITIAL",
        "messageHistory": [
            {
                "timestamp": "2024-01-15T10:30:00Z",
                "role": "user",
                "content": "I feel dizzy",
                "extractedEntities": [
                    {
                        "type": "SYMPTOM",
                        "text": "dizzy",
                        "score": 0.92,
                        "category": "SIGN_OR_SYMPTOM"
                    }
                ]
            }
        ],
        "aggregatedEntities": {"symptoms": ["dizzy"]},
        "followUpCount": 0,
        "emergencyDetected": False
    }
    
    session = ConversationSession.from_dynamodb_item(dynamodb_item)
    
    assert session.session_id == "test-session-456"
    assert session.conversation_state == ConversationState.INITIAL
    assert len(session.message_history) == 1
    assert session.message_history[0].role == MessageRole.USER
    assert session.message_history[0].content == "I feel dizzy"
    assert len(session.message_history[0].extracted_entities) == 1
    assert session.message_history[0].extracted_entities[0].text == "dizzy"


def test_round_trip_serialization():
    """Test that session can be serialized and deserialized without data loss"""
    entity = MedicalEntity(
        type="ANATOMY",
        text="chest",
        score=0.99,
        category="BODY_PART"
    )
    
    message = Message(
        timestamp="2024-01-15T11:00:00Z",
        role=MessageRole.ASSISTANT,
        content="Can you describe the chest pain?",
        extracted_entities=[entity]
    )
    
    original_session = ConversationSession(
        session_id="round-trip-test",
        created_at="2024-01-15T10:00:00Z",
        last_updated_at="2024-01-15T11:00:00Z",
        ttl=1705320000,
        conversation_state=ConversationState.READY_FOR_TRIAGE,
        message_history=[message],
        aggregated_entities={"anatomy": ["chest"], "symptoms": ["pain"]},
        follow_up_count=2,
        emergency_detected=True
    )
    
    # Serialize to DynamoDB format
    item = original_session.to_dynamodb_item()
    
    # Deserialize back to ConversationSession
    restored_session = ConversationSession.from_dynamodb_item(item)
    
    # Verify all fields match
    assert restored_session.session_id == original_session.session_id
    assert restored_session.created_at == original_session.created_at
    assert restored_session.last_updated_at == original_session.last_updated_at
    assert restored_session.ttl == original_session.ttl
    assert restored_session.conversation_state == original_session.conversation_state
    assert restored_session.follow_up_count == original_session.follow_up_count
    assert restored_session.emergency_detected == original_session.emergency_detected
    assert len(restored_session.message_history) == len(original_session.message_history)
    assert restored_session.message_history[0].content == original_session.message_history[0].content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
