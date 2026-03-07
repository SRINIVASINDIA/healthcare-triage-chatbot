"""
Property-based tests for session round-trip consistency
Tests that storing and retrieving a session returns equivalent data

Property 1: Session Creation and Retrieval Round-Trip
Validates: Requirements 1.1, 1.2, 1.3
"""

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck
from datetime import datetime, timezone
import time
from backend.core.models import (
    ConversationSession, 
    ConversationState, 
    Message, 
    MessageRole,
    MedicalEntity
)
from backend.core.session_manager import SessionManager


# Hypothesis strategies for generating test data
@st.composite
def medical_entity_strategy(draw):
    """Generate random MedicalEntity instances"""
    entity_types = ["SYMPTOM", "ANATOMY", "MEDICATION", "MEDICAL_CONDITION", "TIME_EXPRESSION"]
    
    return MedicalEntity(
        type=draw(st.sampled_from(entity_types)),
        text=draw(st.text(min_size=1, max_size=30, alphabet=st.characters(min_codepoint=32, max_codepoint=126))),
        score=draw(st.floats(min_value=0.0, max_value=1.0)),
        category=draw(st.one_of(st.none(), st.text(min_size=1, max_size=20, alphabet=st.characters(min_codepoint=32, max_codepoint=126))))
    )


@st.composite
def message_strategy(draw):
    """Generate random Message instances"""
    return Message(
        timestamp="2024-01-01T00:00:00+00:00",
        role=draw(st.sampled_from(list(MessageRole))),
        content=draw(st.text(min_size=1, max_size=200, alphabet=st.characters(min_codepoint=32, max_codepoint=126))),
        extracted_entities=draw(st.lists(medical_entity_strategy(), max_size=3))
    )


@st.composite
def aggregated_entities_strategy(draw):
    """Generate random aggregated entities dictionary"""
    return {
        "symptoms": draw(st.lists(st.text(min_size=1, max_size=20, alphabet=st.characters(min_codepoint=97, max_codepoint=122)), max_size=3)),
        "anatomy": draw(st.lists(st.text(min_size=1, max_size=20, alphabet=st.characters(min_codepoint=97, max_codepoint=122)), max_size=3)),
        "medications": draw(st.lists(st.text(min_size=1, max_size=20, alphabet=st.characters(min_codepoint=97, max_codepoint=122)), max_size=3)),
        "conditions": draw(st.lists(st.text(min_size=1, max_size=20, alphabet=st.characters(min_codepoint=97, max_codepoint=122)), max_size=3)),
        "timeExpressions": draw(st.lists(st.text(min_size=1, max_size=20, alphabet=st.characters(min_codepoint=97, max_codepoint=122)), max_size=3))
    }


@st.composite
def conversation_session_strategy(draw):
    """Generate random ConversationSession instances"""
    # Use fixed timestamp to avoid flakiness
    base_time = 1700000000  # Fixed base timestamp
    
    return ConversationSession(
        session_id=draw(st.uuids()).hex,
        created_at="2024-01-01T00:00:00+00:00",
        last_updated_at="2024-01-01T00:00:00+00:00",
        ttl=draw(st.integers(min_value=base_time, max_value=base_time + 86400)),
        conversation_state=draw(st.sampled_from(list(ConversationState))),
        message_history=draw(st.lists(message_strategy(), max_size=10)),
        aggregated_entities=draw(aggregated_entities_strategy()),
        follow_up_count=draw(st.integers(min_value=0, max_value=10)),
        emergency_detected=draw(st.booleans())
    )


class TestSessionRoundTrip:
    """
    Property 1: Session Creation and Retrieval Round-Trip
    
    This test validates that:
    - A session can be converted to DynamoDB format (Requirement 1.2)
    - The DynamoDB item can be converted back to a session (Requirement 1.3)
    - The round-trip preserves all data (Requirement 1.1)
    """
    
    @given(session=conversation_session_strategy())
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    def test_session_to_dynamodb_and_back_preserves_data(self, session):
        """
        Property: Converting a session to DynamoDB format and back should preserve all data
        
        This tests the round-trip consistency:
        Session -> to_dynamodb_item() -> from_dynamodb_item() -> Session
        
        The resulting session should be equivalent to the original.
        """
        # Convert session to DynamoDB item format
        dynamodb_item = session.to_dynamodb_item()
        
        # Convert back to session
        restored_session = ConversationSession.from_dynamodb_item(dynamodb_item)
        
        # Verify all fields are preserved
        assert restored_session.session_id == session.session_id
        assert restored_session.created_at == session.created_at
        assert restored_session.last_updated_at == session.last_updated_at
        assert restored_session.ttl == session.ttl
        assert restored_session.conversation_state == session.conversation_state
        assert restored_session.follow_up_count == session.follow_up_count
        assert restored_session.emergency_detected == session.emergency_detected
        
        # Verify aggregated entities
        assert restored_session.aggregated_entities == session.aggregated_entities
        
        # Verify message history length
        assert len(restored_session.message_history) == len(session.message_history)
        
        # Verify each message in history
        for original_msg, restored_msg in zip(session.message_history, restored_session.message_history):
            assert restored_msg.timestamp == original_msg.timestamp
            assert restored_msg.role == original_msg.role
            assert restored_msg.content == original_msg.content
            
            # Verify extracted entities
            assert len(restored_msg.extracted_entities) == len(original_msg.extracted_entities)
            
            for original_entity, restored_entity in zip(original_msg.extracted_entities, restored_msg.extracted_entities):
                assert restored_entity.type == original_entity.type
                assert restored_entity.text == original_entity.text
                assert restored_entity.score == original_entity.score
                assert restored_entity.category == original_entity.category
    
    @given(session=conversation_session_strategy())
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    def test_message_to_dict_and_back_preserves_data(self, session):
        """
        Property: Converting a message to dict format and back should preserve all data
        
        This tests message-level round-trip consistency which is part of session storage.
        """
        for message in session.message_history:
            # Convert message to dict
            message_dict = message.to_dict()
            
            # Verify dict structure
            assert "timestamp" in message_dict
            assert "role" in message_dict
            assert "content" in message_dict
            assert "extractedEntities" in message_dict
            
            # Reconstruct message from dict
            restored_message = Message(
                timestamp=message_dict["timestamp"],
                role=MessageRole(message_dict["role"]),
                content=message_dict["content"],
                extracted_entities=[
                    MedicalEntity(
                        type=entity["type"],
                        text=entity["text"],
                        score=entity["score"],
                        category=entity.get("category")
                    )
                    for entity in message_dict["extractedEntities"]
                ]
            )
            
            # Verify all fields preserved
            assert restored_message.timestamp == message.timestamp
            assert restored_message.role == message.role
            assert restored_message.content == message.content
            assert len(restored_message.extracted_entities) == len(message.extracted_entities)
            
            for original_entity, restored_entity in zip(message.extracted_entities, restored_message.extracted_entities):
                assert restored_entity.type == original_entity.type
                assert restored_entity.text == original_entity.text
                assert restored_entity.score == original_entity.score
                assert restored_entity.category == original_entity.category
    
    @given(session=conversation_session_strategy())
    @settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    def test_dynamodb_item_structure_is_valid(self, session):
        """
        Property: DynamoDB items should have the correct structure
        
        Validates Requirement 1.3: DynamoDB table attributes
        """
        dynamodb_item = session.to_dynamodb_item()
        
        # Verify required keys exist
        required_keys = [
            "sessionId", "createdAt", "lastUpdatedAt", "ttl",
            "conversationState", "messageHistory", "aggregatedEntities",
            "followUpCount", "emergencyDetected"
        ]
        
        for key in required_keys:
            assert key in dynamodb_item, f"Missing required key: {key}"
        
        # Verify data types
        assert isinstance(dynamodb_item["sessionId"], str)
        assert isinstance(dynamodb_item["createdAt"], str)
        assert isinstance(dynamodb_item["lastUpdatedAt"], str)
        assert isinstance(dynamodb_item["ttl"], int)
        assert isinstance(dynamodb_item["conversationState"], str)
        assert isinstance(dynamodb_item["messageHistory"], list)
        assert isinstance(dynamodb_item["aggregatedEntities"], dict)
        assert isinstance(dynamodb_item["followUpCount"], int)
        assert isinstance(dynamodb_item["emergencyDetected"], bool)
        
        # Verify message structure
        for msg in dynamodb_item["messageHistory"]:
            assert "timestamp" in msg
            assert "role" in msg
            assert "content" in msg
            assert "extractedEntities" in msg
            assert isinstance(msg["extractedEntities"], list)
    
    @given(
        session=conversation_session_strategy(),
        iterations=st.integers(min_value=1, max_value=5)
    )
    @settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    def test_multiple_roundtrips_preserve_data(self, session, iterations):
        """
        Property: Multiple round-trips should not degrade data
        
        This ensures that repeated serialization/deserialization cycles
        don't introduce data corruption.
        """
        current_session = session
        
        for _ in range(iterations):
            # Convert to DynamoDB and back
            dynamodb_item = current_session.to_dynamodb_item()
            current_session = ConversationSession.from_dynamodb_item(dynamodb_item)
        
        # After multiple round-trips, data should still match original
        assert current_session.session_id == session.session_id
        assert current_session.conversation_state == session.conversation_state
        assert current_session.follow_up_count == session.follow_up_count
        assert current_session.emergency_detected == session.emergency_detected
        assert len(current_session.message_history) == len(session.message_history)
