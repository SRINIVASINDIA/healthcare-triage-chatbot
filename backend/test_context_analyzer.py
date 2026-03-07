"""
Unit tests for ContextAnalyzer class
"""

import pytest
from datetime import datetime
from backend.core.context_analyzer import ContextAnalyzer
from backend.core.models import ConversationSession, Message, MessageRole, MedicalEntity, ConversationState


def test_get_conversation_context():
    """Test that get_conversation_context returns all required fields"""
    # Create a session with some messages
    session = ConversationSession(
        session_id="test-123",
        created_at=datetime.now().isoformat(),
        last_updated_at=datetime.now().isoformat(),
        ttl=1234567890,
        conversation_state=ConversationState.GATHERING_INFO,
        message_history=[
            Message(
                timestamp=datetime.now().isoformat(),
                role=MessageRole.USER,
                content="I have a headache",
                extracted_entities=[
                    MedicalEntity(type="SYMPTOM", text="headache", score=0.95)
                ]
            )
        ],
        aggregated_entities={"symptoms": ["headache"]},
        follow_up_count=1,
        emergency_detected=False
    )
    
    analyzer = ContextAnalyzer(session)
    context = analyzer.get_conversation_context()
    
    # Verify all required fields are present
    assert "recent_messages" in context
    assert "aggregated_entities" in context
    assert "conversation_state" in context
    assert "follow_up_count" in context
    assert "emergency_detected" in context
    assert "inferred_references" in context
    
    # Verify values
    assert context["conversation_state"] == "GATHERING_INFO"
    assert context["follow_up_count"] == 1
    assert context["emergency_detected"] is False
    assert len(context["recent_messages"]) == 1


def test_get_recent_messages():
    """Test that get_recent_messages returns last N messages"""
    # Create a session with multiple messages
    messages = []
    for i in range(15):
        messages.append(
            Message(
                timestamp=datetime.now().isoformat(),
                role=MessageRole.USER if i % 2 == 0 else MessageRole.ASSISTANT,
                content=f"Message {i}",
                extracted_entities=[]
            )
        )
    
    session = ConversationSession(
        session_id="test-123",
        created_at=datetime.now().isoformat(),
        last_updated_at=datetime.now().isoformat(),
        ttl=1234567890,
        conversation_state=ConversationState.INITIAL,
        message_history=messages,
        aggregated_entities={},
        follow_up_count=0,
        emergency_detected=False
    )
    
    analyzer = ContextAnalyzer(session)
    
    # Test default count (10)
    recent = analyzer.get_recent_messages()
    assert len(recent) == 10
    assert recent[0]["content"] == "Message 5"  # Should start from message 5
    assert recent[-1]["content"] == "Message 14"  # Should end at message 14
    
    # Test custom count
    recent_5 = analyzer.get_recent_messages(count=5)
    assert len(recent_5) == 5
    assert recent_5[0]["content"] == "Message 10"


def test_get_aggregated_entities():
    """Test that get_aggregated_entities returns session entities"""
    session = ConversationSession(
        session_id="test-123",
        created_at=datetime.now().isoformat(),
        last_updated_at=datetime.now().isoformat(),
        ttl=1234567890,
        conversation_state=ConversationState.INITIAL,
        message_history=[],
        aggregated_entities={
            "symptoms": ["headache", "fever"],
            "anatomy": ["head"],
            "medications": ["aspirin"],
            "conditions": [],
            "time_expressions": ["2 days"]
        },
        follow_up_count=0,
        emergency_detected=False
    )
    
    analyzer = ContextAnalyzer(session)
    entities = analyzer.get_aggregated_entities()
    
    assert entities["symptoms"] == ["headache", "fever"]
    assert entities["anatomy"] == ["head"]
    assert entities["medications"] == ["aspirin"]
    assert entities["time_expressions"] == ["2 days"]


def test_infer_references_it():
    """Test that 'it' is resolved to most recent symptom"""
    session = ConversationSession(
        session_id="test-123",
        created_at=datetime.now().isoformat(),
        last_updated_at=datetime.now().isoformat(),
        ttl=1234567890,
        conversation_state=ConversationState.INITIAL,
        message_history=[],
        aggregated_entities={
            "symptoms": ["headache", "nausea"],
            "anatomy": ["head"],
        },
        follow_up_count=0,
        emergency_detected=False
    )
    
    analyzer = ContextAnalyzer(session)
    inferred = analyzer.infer_references("It started yesterday")
    
    assert "it" in inferred
    assert inferred["it"] == "nausea"  # Most recent symptom


def test_infer_references_the_pain():
    """Test that 'the pain' is resolved to pain-related symptom"""
    session = ConversationSession(
        session_id="test-123",
        created_at=datetime.now().isoformat(),
        last_updated_at=datetime.now().isoformat(),
        ttl=1234567890,
        conversation_state=ConversationState.INITIAL,
        message_history=[],
        aggregated_entities={
            "symptoms": ["fever", "chest pain", "headache"],
        },
        follow_up_count=0,
        emergency_detected=False
    )
    
    analyzer = ContextAnalyzer(session)
    inferred = analyzer.infer_references("The pain is getting worse")
    
    assert "the pain" in inferred
    assert inferred["the pain"] == "chest pain"  # Most recent pain symptom


def test_infer_references_there():
    """Test that 'there' is resolved to most recent anatomy location"""
    session = ConversationSession(
        session_id="test-123",
        created_at=datetime.now().isoformat(),
        last_updated_at=datetime.now().isoformat(),
        ttl=1234567890,
        conversation_state=ConversationState.INITIAL,
        message_history=[],
        aggregated_entities={
            "symptoms": ["pain"],
            "anatomy": ["chest", "arm"],
        },
        follow_up_count=0,
        emergency_detected=False
    )
    
    analyzer = ContextAnalyzer(session)
    inferred = analyzer.infer_references("It hurts there")
    
    assert "there" in inferred
    assert inferred["there"] == "arm"  # Most recent anatomy


def test_infer_references_no_entities():
    """Test that infer_references handles empty entities gracefully"""
    session = ConversationSession(
        session_id="test-123",
        created_at=datetime.now().isoformat(),
        last_updated_at=datetime.now().isoformat(),
        ttl=1234567890,
        conversation_state=ConversationState.INITIAL,
        message_history=[],
        aggregated_entities={},
        follow_up_count=0,
        emergency_detected=False
    )
    
    analyzer = ContextAnalyzer(session)
    inferred = analyzer.infer_references("It hurts there")
    
    # Should return empty dict when no entities to reference
    assert inferred == {}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
