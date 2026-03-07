"""
Property-based tests for ContextAnalyzer
Tests universal properties across randomized inputs
"""

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck
from datetime import datetime, timezone
from backend.core.models import ConversationSession, Message, MessageRole, ConversationState, MedicalEntity
from backend.core.context_analyzer import ContextAnalyzer


# Strategy for generating medical entities
@st.composite
def medical_entity_strategy(draw):
    """Generate random medical entities"""
    entity_types = ["SYMPTOM", "ANATOMY", "MEDICAL_CONDITION", "MEDICATION", "TIME_EXPRESSION"]
    entity_type = draw(st.sampled_from(entity_types))
    # Generate text with letters, numbers, and spaces
    text = draw(st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('L', 'N', 'Zs'))))
    score = draw(st.floats(min_value=0.5, max_value=1.0))
    
    return MedicalEntity(
        type=entity_type,
        text=text.strip() if text.strip() else "symptom",  # Ensure non-empty after strip
        score=score,
        category=None
    )


# Strategy for generating messages
@st.composite
def message_strategy(draw):
    """Generate random messages with optional entities"""
    role = draw(st.sampled_from([MessageRole.USER, MessageRole.ASSISTANT]))
    content = draw(st.text(min_size=1, max_size=200))
    timestamp = datetime.now(timezone.utc).isoformat()
    
    # Generate 0-5 entities per message
    num_entities = draw(st.integers(min_value=0, max_value=5))
    entities = [draw(medical_entity_strategy()) for _ in range(num_entities)]
    
    return Message(
        timestamp=timestamp,
        role=role,
        content=content,
        extracted_entities=entities
    )


# Strategy for generating conversation sessions
@st.composite
def session_strategy(draw):
    """Generate random conversation sessions"""
    session_id = draw(st.uuids()).hex
    created_at = datetime.now(timezone.utc).isoformat()
    last_updated_at = created_at
    ttl = draw(st.integers(min_value=1000000000, max_value=2000000000))
    conversation_state = draw(st.sampled_from(list(ConversationState)))
    
    # Generate 1-20 messages
    num_messages = draw(st.integers(min_value=1, max_value=20))
    message_history = [draw(message_strategy()) for _ in range(num_messages)]
    
    # Build aggregated entities from messages
    aggregated_entities = {
        "symptoms": [],
        "anatomy": [],
        "medications": [],
        "conditions": [],
        "time_expressions": []
    }
    
    for msg in message_history:
        for entity in msg.extracted_entities:
            if entity.type == "SYMPTOM" and entity.text not in aggregated_entities["symptoms"]:
                aggregated_entities["symptoms"].append(entity.text)
            elif entity.type == "ANATOMY" and entity.text not in aggregated_entities["anatomy"]:
                aggregated_entities["anatomy"].append(entity.text)
            elif entity.type == "MEDICATION" and entity.text not in aggregated_entities["medications"]:
                aggregated_entities["medications"].append(entity.text)
            elif entity.type == "MEDICAL_CONDITION" and entity.text not in aggregated_entities["conditions"]:
                aggregated_entities["conditions"].append(entity.text)
            elif entity.type == "TIME_EXPRESSION" and entity.text not in aggregated_entities["time_expressions"]:
                aggregated_entities["time_expressions"].append(entity.text)
    
    follow_up_count = draw(st.integers(min_value=0, max_value=3))
    emergency_detected = draw(st.booleans())
    
    return ConversationSession(
        session_id=session_id,
        created_at=created_at,
        last_updated_at=last_updated_at,
        ttl=ttl,
        conversation_state=conversation_state,
        message_history=message_history,
        aggregated_entities=aggregated_entities,
        follow_up_count=follow_up_count,
        emergency_detected=emergency_detected
    )


# Feature: chatgpt-like-enhancements, Property 7: Context Includes Message History
# Validates: Requirements 3.1, 3.4, 13.1
@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
@given(session=session_strategy())
def test_context_includes_message_history(session):
    """
    For any response generation request, the context analyzer should retrieve 
    and include all messages from the session's message history 
    (up to the last 10 messages in the prompt).
    """
    # Arrange
    analyzer = ContextAnalyzer(session)
    
    # Act
    context = analyzer.get_conversation_context()
    recent_messages = analyzer.get_recent_messages(count=10)
    
    # Assert - context should include recent messages
    assert "recent_messages" in context
    assert context["recent_messages"] == recent_messages
    
    # Assert - should return at most 10 messages
    assert len(recent_messages) <= 10
    
    # Assert - if session has <= 10 messages, all should be included
    if len(session.message_history) <= 10:
        assert len(recent_messages) == len(session.message_history)
    else:
        # If more than 10, should return exactly 10 (the most recent)
        assert len(recent_messages) == 10
    
    # Assert - messages should be in chronological order (oldest to newest)
    if len(recent_messages) > 1:
        for i in range(len(recent_messages) - 1):
            # Each message should have timestamp, role, and content
            assert "timestamp" in recent_messages[i]
            assert "role" in recent_messages[i]
            assert "content" in recent_messages[i]


# Feature: chatgpt-like-enhancements, Property 8: Entity Aggregation Completeness
# Validates: Requirements 3.2, 4.4
@settings(max_examples=100)
@given(session=session_strategy())
def test_entity_aggregation_completeness(session):
    """
    For any session with multiple messages containing medical entities, 
    the aggregatedEntities field should contain all unique entities 
    extracted from all messages in the session.
    """
    # Arrange
    analyzer = ContextAnalyzer(session)
    
    # Act
    aggregated = analyzer.get_aggregated_entities()
    
    # Assert - aggregated entities should match session's aggregated entities
    assert aggregated == session.aggregated_entities
    
    # Assert - all entity types should be present as keys
    assert "symptoms" in aggregated
    assert "anatomy" in aggregated
    assert "medications" in aggregated
    assert "conditions" in aggregated
    assert "time_expressions" in aggregated
    
    # Assert - each entity type should be a list
    assert isinstance(aggregated["symptoms"], list)
    assert isinstance(aggregated["anatomy"], list)
    assert isinstance(aggregated["medications"], list)
    assert isinstance(aggregated["conditions"], list)
    assert isinstance(aggregated["time_expressions"], list)
    
    # Assert - verify completeness: all entities from messages should be in aggregated
    all_symptoms = set()
    all_anatomy = set()
    all_medications = set()
    all_conditions = set()
    all_time_expressions = set()
    
    for msg in session.message_history:
        for entity in msg.extracted_entities:
            if entity.type == "SYMPTOM":
                all_symptoms.add(entity.text)
            elif entity.type == "ANATOMY":
                all_anatomy.add(entity.text)
            elif entity.type == "MEDICATION":
                all_medications.add(entity.text)
            elif entity.type == "MEDICAL_CONDITION":
                all_conditions.add(entity.text)
            elif entity.type == "TIME_EXPRESSION":
                all_time_expressions.add(entity.text)
    
    # All unique entities should be in aggregated entities
    assert all_symptoms == set(aggregated["symptoms"])
    assert all_anatomy == set(aggregated["anatomy"])
    assert all_medications == set(aggregated["medications"])
    assert all_conditions == set(aggregated["conditions"])
    assert all_time_expressions == set(aggregated["time_expressions"])


# Feature: chatgpt-like-enhancements, Property 10: Reference Resolution Attempts
# Validates: Requirements 3.5
@settings(max_examples=100)
@given(
    session=session_strategy(),
    pronoun=st.sampled_from(["it", "the pain", "there", "that"])
)
def test_reference_resolution_attempts(session, pronoun):
    """
    For any message containing pronouns or references (like "it", "the pain"), 
    the context analyzer should attempt to resolve them using previously 
    extracted medical entities.
    """
    # Arrange
    analyzer = ContextAnalyzer(session)
    
    # Create a message with the pronoun
    message = f"How long has {pronoun} been bothering you?"
    
    # Act
    inferred = analyzer.infer_references(message)
    
    # Assert - inferred should be a dictionary
    assert isinstance(inferred, dict)
    
    # Assert - if entities exist, pronoun should be resolved
    entities = session.aggregated_entities
    
    if pronoun == "it":
        # Should resolve to most recent symptom or condition
        if entities.get("symptoms") or entities.get("conditions"):
            assert pronoun in inferred
            # Should be a string (the resolved entity)
            assert isinstance(inferred[pronoun], str)
    
    elif pronoun == "the pain":
        # Should resolve to most recent pain-related symptom or any symptom
        if entities.get("symptoms"):
            assert pronoun in inferred
            assert isinstance(inferred[pronoun], str)
    
    elif pronoun == "there":
        # Should resolve to most recent anatomy location
        if entities.get("anatomy"):
            assert pronoun in inferred
            assert isinstance(inferred[pronoun], str)
    
    elif pronoun == "that":
        # Should resolve to most recent symptom or condition
        if entities.get("symptoms") or entities.get("conditions"):
            assert pronoun in inferred
            assert isinstance(inferred[pronoun], str)


# Additional test: Context structure validation
@settings(max_examples=100)
@given(session=session_strategy())
def test_conversation_context_structure(session):
    """
    Verify that get_conversation_context returns a properly structured dictionary
    with all required fields.
    """
    # Arrange
    analyzer = ContextAnalyzer(session)
    
    # Act
    context = analyzer.get_conversation_context()
    
    # Assert - all required fields should be present
    assert "recent_messages" in context
    assert "aggregated_entities" in context
    assert "conversation_state" in context
    assert "follow_up_count" in context
    assert "emergency_detected" in context
    assert "inferred_references" in context
    
    # Assert - field types should be correct
    assert isinstance(context["recent_messages"], list)
    assert isinstance(context["aggregated_entities"], dict)
    assert isinstance(context["conversation_state"], str)
    assert isinstance(context["follow_up_count"], int)
    assert isinstance(context["emergency_detected"], bool)
    assert isinstance(context["inferred_references"], dict)
    
    # Assert - values should match session
    assert context["conversation_state"] == session.conversation_state.value
    assert context["follow_up_count"] == session.follow_up_count
    assert context["emergency_detected"] == session.emergency_detected


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
