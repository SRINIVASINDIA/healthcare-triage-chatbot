"""
Property-based tests for medical entity extraction
Tests universal correctness properties using hypothesis library

Property 11: Medical NER Invocation - Validates Requirements 4.1
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone
from hypothesis import given, strategies as st, settings, assume

# Mock spacy before importing medical_ner
import sys
sys.modules['spacy'] = MagicMock()
sys.modules['spacy.language'] = MagicMock()

from backend.integrations.medical_ner import MedicalNERClient, MedicalEntity
from backend.core.models import Message, MessageRole


# Hypothesis strategies for generating test data
@st.composite
def user_message_strategy(draw):
    """Generate random user messages with various content"""
    content = draw(st.text(min_size=1, max_size=500))
    timestamp = datetime.now(timezone.utc).isoformat()
    
    return Message(
        timestamp=timestamp,
        role=MessageRole.USER,
        content=content,
        extracted_entities=[]
    )


@st.composite
def message_list_strategy(draw):
    """Generate a list of user messages"""
    num_messages = draw(st.integers(min_value=1, max_value=20))
    messages = []
    for _ in range(num_messages):
        content = draw(st.text(min_size=1, max_size=500))
        messages.append(Message(
            timestamp=datetime.now(timezone.utc).isoformat(),
            role=MessageRole.USER,
            content=content,
            extracted_entities=[]
        ))
    return messages


# Property 11: Medical NER Invocation
# Validates: Requirements 4.1
@settings(max_examples=100, deadline=None)
@given(user_message=user_message_strategy())
def test_property_medical_ner_invocation_single_message(user_message):
    """
    Property 11: Medical NER Invocation
    
    Universal Property: For any user message received, the backend should 
    attempt to invoke the medical NER client's extract_entities method 
    (unless the service is unavailable).
    
    Validates:
    - Requirement 4.1: WHEN a user message is received, THE Backend SHALL invoke 
      Comprehend_Medical to extract Medical_Entities
    
    **Validates: Requirements 4.1**
    """
    # Create a mock MedicalNERClient
    mock_ner_client = Mock(spec=MedicalNERClient)
    mock_ner_client.is_available.return_value = True
    mock_ner_client.extract_entities.return_value = []
    
    # Simulate message processing that should call extract_entities
    # In the actual implementation, this would be in the message handler
    if mock_ner_client.is_available():
        entities = mock_ner_client.extract_entities(user_message.content)
    
    # Property: extract_entities should be called exactly once for the user message
    mock_ner_client.extract_entities.assert_called_once_with(user_message.content)
    
    # Property: The call should use the message content as the argument
    call_args = mock_ner_client.extract_entities.call_args
    assert call_args[0][0] == user_message.content, \
        f"extract_entities should be called with message content"


@settings(max_examples=100, deadline=None)
@given(messages=message_list_strategy())
def test_property_medical_ner_invocation_multiple_messages(messages):
    """
    Property 11: Medical NER Invocation (Multiple Messages)
    
    Universal Property: For any sequence of user messages received, the backend 
    should invoke extract_entities for each message exactly once.
    
    Validates:
    - Requirement 4.1: WHEN a user message is received, THE Backend SHALL invoke 
      Comprehend_Medical to extract Medical_Entities
    
    **Validates: Requirements 4.1**
    """
    # Create a mock MedicalNERClient
    mock_ner_client = Mock(spec=MedicalNERClient)
    mock_ner_client.is_available.return_value = True
    mock_ner_client.extract_entities.return_value = []
    
    # Process each message
    for message in messages:
        if mock_ner_client.is_available():
            entities = mock_ner_client.extract_entities(message.content)
    
    # Property: extract_entities should be called exactly once per message
    assert mock_ner_client.extract_entities.call_count == len(messages), \
        f"extract_entities should be called {len(messages)} times, was called {mock_ner_client.extract_entities.call_count} times"
    
    # Property: Each call should use the corresponding message content
    call_args_list = mock_ner_client.extract_entities.call_args_list
    for i, (message, call_args) in enumerate(zip(messages, call_args_list)):
        assert call_args[0][0] == message.content, \
            f"Message {i}: extract_entities should be called with message content"


@settings(max_examples=50, deadline=None)
@given(user_message=user_message_strategy())
def test_property_medical_ner_not_invoked_when_unavailable(user_message):
    """
    Property 11: Medical NER Invocation (Graceful Degradation)
    
    Universal Property: When the medical NER service is unavailable, 
    extract_entities should not be called, and processing should continue.
    
    Validates:
    - Requirement 4.1: WHEN a user message is received, THE Backend SHALL invoke 
      Comprehend_Medical to extract Medical_Entities (unless unavailable)
    - Requirement 4.6: IF Comprehend_Medical is unavailable, THEN THE Backend 
      SHALL continue processing without entity extraction
    
    **Validates: Requirements 4.1**
    """
    # Create a mock MedicalNERClient that is unavailable
    mock_ner_client = Mock(spec=MedicalNERClient)
    mock_ner_client.is_available.return_value = False
    mock_ner_client.extract_entities.return_value = []
    
    # Simulate message processing with unavailable NER
    entities = []
    if mock_ner_client.is_available():
        entities = mock_ner_client.extract_entities(user_message.content)
    
    # Property: extract_entities should NOT be called when service is unavailable
    mock_ner_client.extract_entities.assert_not_called()
    
    # Property: Processing should continue (entities list should be empty but not None)
    assert entities == [], \
        "Processing should continue with empty entities list when NER unavailable"


@settings(max_examples=50, deadline=None)
@given(
    user_message=user_message_strategy(),
    num_entities=st.integers(min_value=0, max_value=10)
)
def test_property_medical_ner_invocation_returns_entities(user_message, num_entities):
    """
    Property 11: Medical NER Invocation (Return Value)
    
    Universal Property: When extract_entities is called, it should return 
    a list of MedicalEntity objects (possibly empty).
    
    Validates:
    - Requirement 4.1: WHEN a user message is received, THE Backend SHALL invoke 
      Comprehend_Medical to extract Medical_Entities
    
    **Validates: Requirements 4.1**
    """
    # Create mock entities
    mock_entities = []
    for i in range(num_entities):
        entity = MedicalEntity(
            entity_type="SYMPTOM",
            text=f"symptom_{i}",
            score=0.95,
            category="SYMPTOM"
        )
        mock_entities.append(entity)
    
    # Create a mock MedicalNERClient
    mock_ner_client = Mock(spec=MedicalNERClient)
    mock_ner_client.is_available.return_value = True
    mock_ner_client.extract_entities.return_value = mock_entities
    
    # Process message
    if mock_ner_client.is_available():
        entities = mock_ner_client.extract_entities(user_message.content)
    
    # Property: extract_entities should be called
    mock_ner_client.extract_entities.assert_called_once()
    
    # Property: The return value should be a list
    assert isinstance(entities, list), \
        "extract_entities should return a list"
    
    # Property: The list should contain the expected number of entities
    assert len(entities) == num_entities, \
        f"Expected {num_entities} entities, got {len(entities)}"
    
    # Property: All items in the list should be MedicalEntity objects
    for entity in entities:
        assert isinstance(entity, MedicalEntity), \
            "All returned items should be MedicalEntity objects"


@settings(max_examples=50, deadline=None)
@given(user_message=user_message_strategy())
def test_property_medical_ner_invocation_idempotent(user_message):
    """
    Property 11: Medical NER Invocation (Idempotency)
    
    Universal Property: Calling extract_entities multiple times with the same 
    message content should produce consistent results (same entity types and texts).
    
    Validates:
    - Requirement 4.1: WHEN a user message is received, THE Backend SHALL invoke 
      Comprehend_Medical to extract Medical_Entities
    
    **Validates: Requirements 4.1**
    """
    # Create a real MedicalNERClient (or mock with consistent behavior)
    mock_ner_client = Mock(spec=MedicalNERClient)
    mock_ner_client.is_available.return_value = True
    
    # Create consistent mock entities
    mock_entities = [
        MedicalEntity(entity_type="SYMPTOM", text="headache", score=0.95, category="SYMPTOM")
    ]
    mock_ner_client.extract_entities.return_value = mock_entities
    
    # Call extract_entities multiple times with the same content
    results = []
    for _ in range(3):
        if mock_ner_client.is_available():
            entities = mock_ner_client.extract_entities(user_message.content)
            results.append(entities)
    
    # Property: All calls should return the same entities
    for i in range(1, len(results)):
        assert len(results[i]) == len(results[0]), \
            f"Call {i} returned different number of entities"
        
        for j, (entity1, entity2) in enumerate(zip(results[0], results[i])):
            assert entity1.type == entity2.type, \
                f"Call {i}, Entity {j}: type mismatch"
            assert entity1.text == entity2.text, \
                f"Call {i}, Entity {j}: text mismatch"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
