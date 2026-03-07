"""
Property-based tests for session management
Tests universal correctness properties using hypothesis library

Property 2: TTL Calculation Consistency - Validates Requirements 1.4, 1.6, 7.3
Property 3: Message Appending Preserves History - Validates Requirements 1.5, 1.7
Property 21: Message History Size Limit - Validates Requirements 7.5, 7.6, 10.1
"""

import pytest
import time
from datetime import datetime, timezone
from hypothesis import given, strategies as st, settings, assume
from moto import mock_aws
import boto3

from core.session_manager import SessionManager
from core.models import (
    ConversationSession, Message, MedicalEntity,
    ConversationState, MessageRole
)


# Hypothesis strategies for generating test data
@st.composite
def message_strategy(draw):
    """Generate random Message objects"""
    role = draw(st.sampled_from([MessageRole.USER, MessageRole.ASSISTANT]))
    content = draw(st.text(min_size=1, max_size=500))
    timestamp = datetime.now(timezone.utc).isoformat()
    
    # Generate 0-5 medical entities
    num_entities = draw(st.integers(min_value=0, max_value=5))
    entities = []
    for _ in range(num_entities):
        entity = MedicalEntity(
            type=draw(st.sampled_from(["SYMPTOM", "ANATOMY", "MEDICATION", "MEDICAL_CONDITION", "TIME_EXPRESSION"])),
            text=draw(st.text(min_size=1, max_size=50)),
            score=draw(st.floats(min_value=0.0, max_value=1.0)),
            category=draw(st.one_of(st.none(), st.text(min_size=1, max_size=50)))
        )
        entities.append(entity)
    
    return Message(
        timestamp=timestamp,
        role=role,
        content=content,
        extracted_entities=entities
    )


def create_mock_dynamodb_and_session_manager():
    """Create mock DynamoDB table and SessionManager instance"""
    # Create mock DynamoDB table
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
    table = dynamodb.create_table(
        TableName='test-conversations',
        KeySchema=[
            {'AttributeName': 'sessionId', 'KeyType': 'HASH'}
        ],
        AttributeDefinitions=[
            {'AttributeName': 'sessionId', 'AttributeType': 'S'}
        ],
        BillingMode='PAY_PER_REQUEST'
    )
    
    return SessionManager(table_name='test-conversations')


# Property 2: TTL Calculation Consistency
# Validates: Requirements 1.4, 1.6, 7.3
@settings(max_examples=100, deadline=None)
@given(
    session_id=st.text(min_size=1, max_size=100),
    initial_delay=st.integers(min_value=0, max_value=5)
)
@mock_aws
def test_property_ttl_calculation_consistency(session_id, initial_delay):
    """
    Property 2: TTL Calculation Consistency
    
    Universal Property: For any session, the TTL should always be set to 
    current_timestamp + 24_hours (86400 seconds) whenever the session is 
    created or updated.
    
    Validates:
    - Requirement 1.4: Session_Manager SHALL set Session_TTL to 24 hours from lastUpdatedAt
    - Requirement 1.6: Session_Manager SHALL update lastUpdatedAt and reset Session_TTL with each new message
    - Requirement 7.3: Session_Manager SHALL set TTL to current timestamp plus 86400 seconds (24 hours)
    """
    # Create session manager with mock DynamoDB
    session_manager = create_mock_dynamodb_and_session_manager()
    
    # Record time before creating session
    time_before_create = int(time.time())
    
    # Optional delay to simulate time passing
    if initial_delay > 0:
        time.sleep(initial_delay)
    
    # Create a new session
    session = session_manager.create_session(session_id=session_id)
    
    # Record time after creating session
    time_after_create = int(time.time())
    
    # Property: TTL should be approximately current_time + 86400 seconds
    expected_ttl_min = time_before_create + 86400
    expected_ttl_max = time_after_create + 86400
    
    assert expected_ttl_min <= session.ttl <= expected_ttl_max, \
        f"TTL {session.ttl} not in expected range [{expected_ttl_min}, {expected_ttl_max}]"
    
    # Wait a moment to ensure time difference
    time.sleep(0.1)
    
    # Update the session
    time_before_update = int(time.time())
    session_manager.update_session(session)
    time_after_update = int(time.time())
    
    # Retrieve the updated session
    updated_session = session_manager.get_session(session_id)
    
    # Property: TTL should be recalculated to current_time + 86400 seconds
    expected_ttl_min_updated = time_before_update + 86400
    expected_ttl_max_updated = time_after_update + 86400
    
    assert expected_ttl_min_updated <= updated_session.ttl <= expected_ttl_max_updated, \
        f"Updated TTL {updated_session.ttl} not in expected range [{expected_ttl_min_updated}, {expected_ttl_max_updated}]"
    
    # Property: TTL should have increased (since time has passed)
    assert updated_session.ttl >= session.ttl, \
        "TTL should increase or stay the same after update"


# Property 3: Message Appending Preserves History
# Validates: Requirements 1.5, 1.7
@settings(max_examples=100, deadline=None)
@given(
    session_id=st.text(min_size=1, max_size=100),
    messages=st.lists(message_strategy(), min_size=1, max_size=20)
)
@mock_aws
def test_property_message_appending_preserves_history(session_id, messages):
    """
    Property 3: Message Appending Preserves History
    
    Universal Property: For any sequence of messages appended to a session,
    the message history should preserve all messages in the order they were added,
    and the content of each message should remain unchanged.
    
    Validates:
    - Requirement 1.5: Session_Manager SHALL retrieve existing Conversation_Session and append new message to Message_History
    - Requirement 1.7: Message_History SHALL store messages as JSON objects containing: timestamp, role, content, and extractedEntities
    """
    # Create session manager with mock DynamoDB
    session_manager = create_mock_dynamodb_and_session_manager()
    
    # Create a new session
    session = session_manager.create_session(session_id=session_id)
    
    # Track all messages we append
    appended_messages = []
    
    # Append each message one by one
    for message in messages:
        success = session_manager.append_message(session_id, message)
        assert success, f"Failed to append message: {message.content[:50]}"
        appended_messages.append(message)
        
        # Retrieve session after each append
        retrieved_session = session_manager.get_session(session_id)
        
        # Property: Number of messages in history should match number appended
        assert len(retrieved_session.message_history) == len(appended_messages), \
            f"Expected {len(appended_messages)} messages, got {len(retrieved_session.message_history)}"
        
        # Property: Messages should be in the same order
        for i, (original, stored) in enumerate(zip(appended_messages, retrieved_session.message_history)):
            assert stored.role == original.role, \
                f"Message {i}: role mismatch - expected {original.role}, got {stored.role}"
            assert stored.content == original.content, \
                f"Message {i}: content mismatch"
            assert len(stored.extracted_entities) == len(original.extracted_entities), \
                f"Message {i}: entity count mismatch"
            
            # Verify entity details are preserved
            for j, (orig_entity, stored_entity) in enumerate(zip(original.extracted_entities, stored.extracted_entities)):
                assert stored_entity.type == orig_entity.type, \
                    f"Message {i}, Entity {j}: type mismatch"
                assert stored_entity.text == orig_entity.text, \
                    f"Message {i}, Entity {j}: text mismatch"
                assert abs(stored_entity.score - orig_entity.score) < 0.0001, \
                    f"Message {i}, Entity {j}: score mismatch"


# Property 21: Message History Size Limit
# Validates: Requirements 7.5, 7.6, 10.1
@settings(max_examples=100, deadline=None)
@given(
    session_id=st.text(min_size=1, max_size=100),
    num_messages=st.integers(min_value=51, max_value=100)
)
@mock_aws
def test_property_message_history_size_limit(session_id, num_messages):
    """
    Property 21: Message History Size Limit
    
    Universal Property: For any session, regardless of how many messages are appended,
    the message history should never exceed 50 messages. When the limit is exceeded,
    the oldest messages should be removed to maintain the limit.
    
    Validates:
    - Requirement 7.5: DynamoDB_Table SHALL limit Message_History to 50 messages per session
    - Requirement 7.6: WHEN Message_History exceeds 50 messages, Session_Manager SHALL remove oldest messages
    - Requirement 10.1: Backend SHALL support conversations with up to 50 message exchanges
    """
    # Create session manager with mock DynamoDB
    session_manager = create_mock_dynamodb_and_session_manager()
    
    # Create a new session
    session = session_manager.create_session(session_id=session_id)
    
    # Generate messages with identifiable content
    messages = []
    for i in range(num_messages):
        message = Message(
            timestamp=datetime.now(timezone.utc).isoformat(),
            role=MessageRole.USER if i % 2 == 0 else MessageRole.ASSISTANT,
            content=f"Message number {i}",
            extracted_entities=[]
        )
        messages.append(message)
    
    # Append all messages
    for message in messages:
        session_manager.append_message(session_id, message)
    
    # Retrieve the final session
    final_session = session_manager.get_session(session_id)
    
    # Property: Message history should never exceed 50 messages
    assert len(final_session.message_history) <= 50, \
        f"Message history has {len(final_session.message_history)} messages, exceeds limit of 50"
    
    # Property: Should contain exactly 50 messages (since we added more than 50)
    assert len(final_session.message_history) == 50, \
        f"Expected exactly 50 messages, got {len(final_session.message_history)}"
    
    # Property: Should contain the LAST 50 messages (oldest removed)
    expected_start_index = num_messages - 50
    for i, stored_message in enumerate(final_session.message_history):
        expected_message_num = expected_start_index + i
        expected_content = f"Message number {expected_message_num}"
        assert stored_message.content == expected_content, \
            f"Message {i}: expected '{expected_content}', got '{stored_message.content}'"
    
    # Property: First message in history should be message #(num_messages - 50)
    first_message = final_session.message_history[0]
    assert first_message.content == f"Message number {expected_start_index}", \
        f"First message should be 'Message number {expected_start_index}', got '{first_message.content}'"
    
    # Property: Last message in history should be message #(num_messages - 1)
    last_message = final_session.message_history[-1]
    assert last_message.content == f"Message number {num_messages - 1}", \
        f"Last message should be 'Message number {num_messages - 1}', got '{last_message.content}'"


# Additional property test: Verify limit enforcement at boundary
@settings(max_examples=50, deadline=None)
@given(
    session_id=st.text(min_size=1, max_size=100)
)
@mock_aws
def test_property_message_limit_boundary(session_id):
    """
    Property 21 (Boundary Test): Message History Size Limit at Boundary
    
    Tests the exact boundary condition when transitioning from 50 to 51 messages.
    """
    # Create session manager with mock DynamoDB
    session_manager = create_mock_dynamodb_and_session_manager()
    
    # Create session
    session = session_manager.create_session(session_id=session_id)
    
    # Add exactly 50 messages
    for i in range(50):
        message = Message(
            timestamp=datetime.now(timezone.utc).isoformat(),
            role=MessageRole.USER,
            content=f"Message {i}",
            extracted_entities=[]
        )
        session_manager.append_message(session_id, message)
    
    # Verify we have exactly 50 messages
    session_50 = session_manager.get_session(session_id)
    assert len(session_50.message_history) == 50
    assert session_50.message_history[0].content == "Message 0"
    assert session_50.message_history[-1].content == "Message 49"
    
    # Add one more message (51st)
    message_51 = Message(
        timestamp=datetime.now(timezone.utc).isoformat(),
        role=MessageRole.USER,
        content="Message 50",
        extracted_entities=[]
    )
    session_manager.append_message(session_id, message_51)
    
    # Verify still exactly 50 messages, oldest removed
    session_51 = session_manager.get_session(session_id)
    assert len(session_51.message_history) == 50
    assert session_51.message_history[0].content == "Message 1"  # Message 0 removed
    assert session_51.message_history[-1].content == "Message 50"  # New message added


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
