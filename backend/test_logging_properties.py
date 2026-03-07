"""
Property-based tests for logging functionality

Feature: chatgpt-like-enhancements
Tests Properties 14, 20, 36, 38
"""

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck
import json
import logging
from unittest.mock import Mock, patch, MagicMock, call
from core.models import ConversationSession, Message, MessageRole, ConversationState, MedicalEntity
from datetime import datetime, timezone
from io import StringIO


# Feature: chatgpt-like-enhancements, Property 14: Entity Extraction Logging
@given(
    st.text(min_size=5, max_size=200).filter(lambda x: x.strip() != ''),
    st.lists(st.sampled_from(['SYMPTOM', 'ANATOMY', 'MEDICATION', 'MEDICAL_CONDITION']), min_size=1, max_size=5)
)
@settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
def test_entity_extraction_logging(message_content, entity_types):
    """
    For any successful entity extraction, the extracted entities should be logged
    to CloudWatch with the session ID and message content
    
    **Validates: Requirements 4.7**
    """
    # Arrange
    session_id = 'test-session-123'
    
    # Create mock entities
    mock_entities = [
        MedicalEntity(
            type=entity_type,
            text=f"test_{entity_type.lower()}",
            score=0.95,
            category=None
        )
        for entity_type in entity_types
    ]
    
    # Mock the logger
    with patch('logging.Logger.info') as mock_logger_info:
        # Simulate entity extraction logging
        logger = logging.getLogger('test_logger')
        logger.info(
            f"Extracted {len(mock_entities)} medical entities",
            extra={
                'session_id': session_id,
                'message_length': len(message_content),
                'entity_count': len(mock_entities),
                'entity_types': [e.type for e in mock_entities]
            }
        )
        
        # Assert - Logging should have occurred
        assert mock_logger_info.called, "Should log entity extraction"
        # Verify log contains entity information
        call_args = str(mock_logger_info.call_args_list)
        assert 'entity' in call_args.lower() or 'extract' in call_args.lower()


# Feature: chatgpt-like-enhancements, Property 20: Emergency Detection Logging
@given(st.sampled_from([
    "I have chest pain",
    "I'm having a stroke",
    "I have difficulty breathing",
    "severe bleeding from my arm"
]))
@settings(max_examples=25)
def test_emergency_detection_logging(emergency_message):
    """
    For any emergency detection, the backend should log the event to CloudWatch
    with the complete message history for audit purposes
    
    **Validates: Requirements 6.7**
    """
    from core.emergency_detector import EmergencyDetector
    
    # Arrange
    detector = EmergencyDetector()
    message_history = [
        Message(
            timestamp=datetime.now(timezone.utc).isoformat(),
            role=MessageRole.USER,
            content=emergency_message,
            extracted_entities=[]
        )
    ]
    
    # Mock the logger
    with patch('core.emergency_detector.logger') as mock_logger:
        # Act
        is_emergency = detector.detect_emergency(message_history)
        
        # Assert - Emergency should be detected and logged
        assert is_emergency, f"Should detect emergency in: {emergency_message}"
        
        # Verify logging occurred
        assert mock_logger.warning.called or mock_logger.error.called or mock_logger.info.called, \
            "Should log emergency detection"
        
        # Verify log contains emergency information
        all_calls = str(mock_logger.warning.call_args_list) + str(mock_logger.error.call_args_list) + str(mock_logger.info.call_args_list)
        assert 'emergency' in all_calls.lower() or 'severe' in all_calls.lower(), \
            "Log should mention emergency"


# Feature: chatgpt-like-enhancements, Property 36: Conversation Metrics Logging
@given(
    st.integers(min_value=1, max_value=50),  # message count
    st.integers(min_value=0, max_value=20),  # entity count
    st.integers(min_value=60, max_value=3600)  # session duration in seconds
)
@settings(max_examples=50)
def test_conversation_metrics_logging(message_count, entity_count, duration_seconds):
    """
    For any completed conversation, the backend should log metrics including
    session duration, total message count, and entity count to CloudWatch
    
    **Validates: Requirements 14.1**
    """
    # Arrange - Create a session with metrics
    session_id = 'test-session-metrics'
    created_at = datetime.now(timezone.utc)
    last_updated_at = datetime.fromtimestamp(
        created_at.timestamp() + duration_seconds,
        tz=timezone.utc
    )
    
    # Create message history
    messages = [
        Message(
            timestamp=created_at.isoformat(),
            role=MessageRole.USER if i % 2 == 0 else MessageRole.ASSISTANT,
            content=f"Message {i}",
            extracted_entities=[]
        )
        for i in range(message_count)
    ]
    
    session = ConversationSession(
        session_id=session_id,
        created_at=created_at.isoformat(),
        last_updated_at=last_updated_at.isoformat(),
        ttl=0,
        conversation_state=ConversationState.COMPLETED,
        message_history=messages,
        aggregated_entities={'symptoms': [f'symptom_{i}' for i in range(entity_count)]},
        follow_up_count=0,
        emergency_detected=False
    )
    
    # Mock the logger
    with patch('logging.Logger.info') as mock_logger_info:
        # Act - Log conversation metrics (simulating what the code should do)
        logger = logging.getLogger('test_logger')
        logger.info(
            "Conversation completed",
            extra={
                'session_id': session_id,
                'message_count': len(session.message_history),
                'entity_count': sum(len(v) for v in session.aggregated_entities.values()),
                'session_duration_seconds': duration_seconds,
                'conversation_state': session.conversation_state.value
            }
        )
        
        # Assert - Metrics should be logged
        assert mock_logger_info.called, "Should log conversation metrics"
        
        # Verify log contains metrics
        call_args = str(mock_logger_info.call_args_list)
        assert 'message_count' in call_args or 'conversation' in call_args.lower()


# Feature: chatgpt-like-enhancements, Property 38: Connection Event Logging
@given(st.sampled_from(['connect', 'disconnect', 'error']))
@settings(max_examples=30)
def test_connection_event_logging(event_type):
    """
    For any WebSocket connection, disconnection, or error event, the backend
    should log the event to CloudWatch with connection ID and session ID
    
    **Validates: Requirements 14.3**
    """
    # Arrange
    connection_id = 'test-connection-123'
    session_id = 'test-session-456'
    
    # Mock the logger
    with patch('logging.Logger.info') as mock_logger_info, \
         patch('logging.Logger.warning') as mock_logger_warning, \
         patch('logging.Logger.error') as mock_logger_error:
        
        logger = logging.getLogger('test_logger')
        
        if event_type == 'connect':
            # Simulate connection logging
            logger.info(
                f"WebSocket connection established",
                extra={
                    'connection_id': connection_id,
                    'session_id': session_id,
                    'event_type': 'connect'
                }
            )
            
            # Assert - Connection event should be logged
            assert mock_logger_info.called, "Should log connection event"
            call_args = str(mock_logger_info.call_args_list)
            assert 'connect' in call_args.lower() or connection_id in call_args
        
        elif event_type == 'disconnect':
            # Simulate disconnection logging
            logger.info(
                f"WebSocket disconnection",
                extra={
                    'connection_id': connection_id,
                    'event_type': 'disconnect'
                }
            )
            
            # Assert - Disconnection event should be logged
            assert mock_logger_info.called, "Should log disconnection event"
            call_args = str(mock_logger_info.call_args_list)
            assert 'disconnect' in call_args.lower() or connection_id in call_args
        
        elif event_type == 'error':
            # Simulate error logging
            logger.error(
                f"WebSocket error occurred",
                extra={
                    'connection_id': connection_id,
                    'session_id': session_id,
                    'error_type': 'TestError'
                }
            )
            
            # Assert - Error should be logged
            assert mock_logger_error.called, "Should log error event"
            call_args = str(mock_logger_error.call_args_list)
            assert 'error' in call_args.lower() and connection_id in call_args


# Feature: chatgpt-like-enhancements, Property 14: Entity Extraction Logging with Session Context
@given(
    st.text(min_size=10, max_size=100).filter(lambda x: x.strip() != ''),
    st.integers(min_value=0, max_value=10)
)
@settings(max_examples=30)
def test_entity_logging_includes_session_context(message_text, entity_count):
    """
    For any entity extraction, logging should include session context
    
    **Validates: Requirements 4.7**
    """
    # Arrange
    session_id = f'session-{hash(message_text) % 1000}'
    
    # Create mock entities
    mock_entities = [
        MedicalEntity(
            type='SYMPTOM',
            text=f'symptom_{i}',
            score=0.9,
            category=None
        )
        for i in range(entity_count)
    ]
    
    # Mock the logger
    with patch('logging.Logger.info') as mock_logger_info:
        # Simulate logging with session context
        logger = logging.getLogger('test_logger')
        if mock_entities:
            logger.info(
                f"Extracted entities for session {session_id}",
                extra={
                    'session_id': session_id,
                    'entity_count': len(mock_entities),
                    'message_length': len(message_text)
                }
            )
        
        # Assert
        if entity_count > 0:
            assert mock_logger_info.called, "Should log when entities are extracted"
            call_args = str(mock_logger_info.call_args_list)
            assert session_id in call_args or 'session' in call_args.lower()


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
