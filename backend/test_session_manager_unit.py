"""
Unit tests for SessionManager (with mocked DynamoDB)
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timezone
from core.session_manager import SessionManager
from core.models import (
    ConversationSession, Message, MedicalEntity,
    ConversationState, MessageRole
)


@pytest.fixture
def mock_dynamodb_table():
    """Create a mock DynamoDB table"""
    with patch('boto3.resource') as mock_resource:
        mock_table = MagicMock()
        mock_resource.return_value.Table.return_value = mock_table
        yield mock_table


def test_create_session(mock_dynamodb_table):
    """Test creating a new session"""
    manager = SessionManager("test-table")
    
    # Mock successful put_item
    mock_dynamodb_table.put_item.return_value = {}
    
    session = manager.create_session()
    
    assert session is not None
    assert session.session_id is not None
    assert session.conversation_state == ConversationState.INITIAL
    assert len(session.message_history) == 0
    assert session.follow_up_count == 0
    assert session.emergency_detected is False
    
    # Verify put_item was called
    mock_dynamodb_table.put_item.assert_called_once()


def test_create_session_with_custom_id(mock_dynamodb_table):
    """Test creating a session with a custom ID"""
    manager = SessionManager("test-table")
    
    mock_dynamodb_table.put_item.return_value = {}
    
    custom_id = "my-custom-session-id"
    session = manager.create_session(session_id=custom_id)
    
    assert session.session_id == custom_id


def test_get_session_found(mock_dynamodb_table):
    """Test retrieving an existing session"""
    manager = SessionManager("test-table")
    
    # Mock DynamoDB response
    mock_dynamodb_table.get_item.return_value = {
        'Item': {
            'sessionId': 'test-123',
            'createdAt': '2024-01-15T10:00:00Z',
            'lastUpdatedAt': '2024-01-15T10:30:00Z',
            'ttl': 1705320000,
            'conversationState': 'INITIAL',
            'messageHistory': [],
            'aggregatedEntities': {},
            'followUpCount': 0,
            'emergencyDetected': False
        }
    }
    
    session = manager.get_session('test-123')
    
    assert session is not None
    assert session.session_id == 'test-123'
    assert session.conversation_state == ConversationState.INITIAL


def test_get_session_not_found(mock_dynamodb_table):
    """Test retrieving a non-existent session"""
    manager = SessionManager("test-table")
    
    # Mock DynamoDB response with no item
    mock_dynamodb_table.get_item.return_value = {}
    
    session = manager.get_session('non-existent')
    
    assert session is None


def test_update_session(mock_dynamodb_table):
    """Test updating a session"""
    manager = SessionManager("test-table")
    
    mock_dynamodb_table.put_item.return_value = {}
    
    session = ConversationSession(
        session_id='update-test',
        created_at='2024-01-15T10:00:00Z',
        last_updated_at='2024-01-15T10:00:00Z',
        ttl=1705320000,
        conversation_state=ConversationState.GATHERING_INFO,
        message_history=[],
        aggregated_entities={},
        follow_up_count=1,
        emergency_detected=False
    )
    
    result = manager.update_session(session)
    
    assert result is True
    mock_dynamodb_table.put_item.assert_called_once()


def test_append_message_enforces_limit(mock_dynamodb_table):
    """Test that append_message enforces 50-message limit"""
    manager = SessionManager("test-table")
    
    # Create a session with 50 messages
    messages = [
        Message(
            timestamp=f'2024-01-15T10:{i:02d}:00Z',
            role=MessageRole.USER if i % 2 == 0 else MessageRole.ASSISTANT,
            content=f'Message {i}',
            extracted_entities=[]
        )
        for i in range(50)
    ]
    
    session = ConversationSession(
        session_id='limit-test',
        created_at='2024-01-15T10:00:00Z',
        last_updated_at='2024-01-15T10:00:00Z',
        ttl=1705320000,
        conversation_state=ConversationState.GATHERING_INFO,
        message_history=messages,
        aggregated_entities={},
        follow_up_count=0,
        emergency_detected=False
    )
    
    # Mock get_session to return our session
    mock_dynamodb_table.get_item.return_value = {
        'Item': session.to_dynamodb_item()
    }
    mock_dynamodb_table.put_item.return_value = {}
    
    # Append a new message
    new_message = Message(
        timestamp='2024-01-15T11:00:00Z',
        role=MessageRole.USER,
        content='Message 51',
        extracted_entities=[]
    )
    
    result = manager.append_message('limit-test', new_message)
    
    assert result is True
    
    # Verify put_item was called and check the message count
    call_args = mock_dynamodb_table.put_item.call_args
    updated_item = call_args[1]['Item']
    
    # Should still have exactly 50 messages (oldest removed)
    assert len(updated_item['messageHistory']) == 50
    # The newest message should be our new one
    assert updated_item['messageHistory'][-1]['content'] == 'Message 51'
    # The oldest message (Message 0) should be removed
    assert updated_item['messageHistory'][0]['content'] == 'Message 1'


def test_append_message_updates_aggregated_entities(mock_dynamodb_table):
    """Test that append_message updates aggregated entities"""
    manager = SessionManager("test-table")
    
    session = ConversationSession(
        session_id='entity-test',
        created_at='2024-01-15T10:00:00Z',
        last_updated_at='2024-01-15T10:00:00Z',
        ttl=1705320000,
        conversation_state=ConversationState.GATHERING_INFO,
        message_history=[],
        aggregated_entities={
            'symptoms': [],
            'anatomy': [],
            'medications': [],
            'conditions': [],
            'timeExpressions': []
        },
        follow_up_count=0,
        emergency_detected=False
    )
    
    mock_dynamodb_table.get_item.return_value = {
        'Item': session.to_dynamodb_item()
    }
    mock_dynamodb_table.put_item.return_value = {}
    
    # Create message with entities
    message = Message(
        timestamp='2024-01-15T10:30:00Z',
        role=MessageRole.USER,
        content='I have a headache',
        extracted_entities=[
            MedicalEntity(type='SYMPTOM', text='headache', score=0.95),
            MedicalEntity(type='ANATOMY', text='head', score=0.98)
        ]
    )
    
    result = manager.append_message('entity-test', message)
    
    assert result is True
    
    # Verify aggregated entities were updated
    call_args = mock_dynamodb_table.put_item.call_args
    updated_item = call_args[1]['Item']
    
    assert 'headache' in updated_item['aggregatedEntities']['symptoms']
    assert 'head' in updated_item['aggregatedEntities']['anatomy']


def test_update_ttl(mock_dynamodb_table):
    """Test updating TTL for a session"""
    manager = SessionManager("test-table")
    
    session = ConversationSession(
        session_id='ttl-test',
        created_at='2024-01-15T10:00:00Z',
        last_updated_at='2024-01-15T10:00:00Z',
        ttl=1705320000,
        conversation_state=ConversationState.INITIAL,
        message_history=[],
        aggregated_entities={},
        follow_up_count=0,
        emergency_detected=False
    )
    
    mock_dynamodb_table.get_item.return_value = {
        'Item': session.to_dynamodb_item()
    }
    mock_dynamodb_table.put_item.return_value = {}
    
    result = manager.update_ttl('ttl-test')
    
    assert result is True
    
    # Verify TTL was updated
    call_args = mock_dynamodb_table.put_item.call_args
    updated_item = call_args[1]['Item']
    
    # TTL should be greater than the original
    assert updated_item['ttl'] > 1705320000


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
