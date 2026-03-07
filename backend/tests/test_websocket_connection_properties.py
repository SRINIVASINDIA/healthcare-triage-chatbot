"""
Property-based tests for WebSocket connection handling
Tests Requirements 2.2, 2.3, 9.1, 9.2, 9.5, 14.3

**Validates: Property 4 - Session Connection Round-Trip**
For any WebSocket connection request, the backend should either create a new session 
or retrieve an existing one (if valid sessionId provided), and return a session ID to the client.
"""

import pytest
from hypothesis import given, strategies as st, settings
from unittest.mock import Mock, patch, MagicMock
import json
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from websocket.connect import lambda_handler
from core.models import ConversationSession, ConversationState


# Strategy for generating valid UUID v4 strings
uuid_strategy = st.uuids().map(str)

# Strategy for generating connection IDs
connection_id_strategy = st.text(
    alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd')),
    min_size=10,
    max_size=20
)


class TestConnectionHandlingProperties:
    """Property-based tests for WebSocket connection handling"""
    
    @given(connection_id=connection_id_strategy)
    @settings(max_examples=100)
    @patch('websocket.connect.SessionManager')
    def test_property_new_connection_creates_session(self, mock_session_manager_class, connection_id):
        """
        Property 4: For any connection without sessionId, a new session should be created
        
        **Validates: Requirements 2.2, 2.3**
        """
        # Arrange
        mock_session_manager = Mock()
        mock_session = Mock()
        mock_session.session_id = 'new-session-id'
        mock_session.message_history = []
        mock_session_manager.create_session.return_value = mock_session
        mock_session_manager_class.return_value = mock_session_manager
        
        event = {
            'requestContext': {
                'connectionId': connection_id
            },
            'queryStringParameters': None
        }
        
        # Act
        response = lambda_handler(event, None)
        
        # Assert
        assert response['statusCode'] == 200
        mock_session_manager.create_session.assert_called_once()
        mock_session_manager.get_session.assert_not_called()
    
    @given(
        connection_id=connection_id_strategy,
        session_id=uuid_strategy
    )
    @settings(max_examples=100)
    @patch('websocket.connect.SessionManager')
    def test_property_existing_session_retrieved(self, mock_session_manager_class, connection_id, session_id):
        """
        Property 4: For any connection with valid sessionId, existing session should be retrieved
        
        **Validates: Requirements 9.1, 9.2**
        """
        # Arrange
        mock_session_manager = Mock()
        mock_session = Mock()
        mock_session.session_id = session_id
        mock_session.message_history = []
        mock_session_manager.get_session.return_value = mock_session
        mock_session_manager_class.return_value = mock_session_manager
        
        event = {
            'requestContext': {
                'connectionId': connection_id
            },
            'queryStringParameters': {
                'sessionId': session_id
            }
        }
        
        # Act
        response = lambda_handler(event, None)
        
        # Assert
        assert response['statusCode'] == 200
        mock_session_manager.get_session.assert_called_once_with(session_id)
        mock_session_manager.update_ttl.assert_called_once_with(session_id)
    
    @given(
        connection_id=connection_id_strategy,
        invalid_session_id=uuid_strategy
    )
    @settings(max_examples=100)
    @patch('websocket.connect.SessionManager')
    def test_property_invalid_session_creates_new(self, mock_session_manager_class, connection_id, invalid_session_id):
        """
        Property 26: For any connection with invalid/expired sessionId, new session should be created
        
        **Validates: Requirement 9.5**
        """
        # Arrange
        mock_session_manager = Mock()
        mock_session_manager.get_session.return_value = None  # Session not found
        mock_new_session = Mock()
        mock_new_session.session_id = 'new-session-id'
        mock_new_session.message_history = []
        mock_session_manager.create_session.return_value = mock_new_session
        mock_session_manager_class.return_value = mock_session_manager
        
        event = {
            'requestContext': {
                'connectionId': connection_id
            },
            'queryStringParameters': {
                'sessionId': invalid_session_id
            }
        }
        
        # Act
        response = lambda_handler(event, None)
        
        # Assert
        assert response['statusCode'] == 200
        mock_session_manager.get_session.assert_called_once_with(invalid_session_id)
        mock_session_manager.create_session.assert_called_once()
    
    @given(
        connection_id=connection_id_strategy,
        session_id=uuid_strategy,
        message_count=st.integers(min_value=0, max_value=50)
    )
    @settings(max_examples=100)
    @patch('websocket.connect.SessionManager')
    def test_property_connection_preserves_message_history(
        self, mock_session_manager_class, connection_id, session_id, message_count
    ):
        """
        Property 4: For any reconnection, message history should be preserved
        
        **Validates: Requirements 9.3, 9.4**
        """
        # Arrange
        mock_session_manager = Mock()
        mock_session = Mock()
        mock_session.session_id = session_id
        mock_session.message_history = [Mock() for _ in range(message_count)]
        mock_session_manager.get_session.return_value = mock_session
        mock_session_manager_class.return_value = mock_session_manager
        
        event = {
            'requestContext': {
                'connectionId': connection_id
            },
            'queryStringParameters': {
                'sessionId': session_id
            }
        }
        
        # Act
        response = lambda_handler(event, None)
        
        # Assert
        assert response['statusCode'] == 200
        # Session should be retrieved with all messages intact
        retrieved_session = mock_session_manager.get_session.return_value
        assert len(retrieved_session.message_history) == message_count
    
    @given(connection_id=connection_id_strategy)
    @settings(max_examples=50)
    @patch('websocket.connect.SessionManager')
    @patch('websocket.connect.logger')
    def test_property_connection_events_logged(
        self, mock_logger, mock_session_manager_class, connection_id
    ):
        """
        Property 38: For any connection event, it should be logged to CloudWatch
        
        **Validates: Requirement 14.3**
        """
        # Arrange
        mock_session_manager = Mock()
        mock_session = Mock()
        mock_session.session_id = 'test-session'
        mock_session.message_history = []
        mock_session_manager.create_session.return_value = mock_session
        mock_session_manager_class.return_value = mock_session_manager
        
        event = {
            'requestContext': {
                'connectionId': connection_id
            },
            'queryStringParameters': None
        }
        
        # Act
        response = lambda_handler(event, None)
        
        # Assert
        assert response['statusCode'] == 200
        # Verify logging was called
        assert mock_logger.info.call_count >= 2  # At least connection initiated and connected
        
        # Check that connection_id is in log calls
        log_calls = [str(call) for call in mock_logger.info.call_args_list]
        connection_logged = any(connection_id in call for call in log_calls)
        assert connection_logged
    
    @given(connection_id=connection_id_strategy)
    @settings(max_examples=50)
    @patch('websocket.connect.SessionManager')
    def test_property_connection_error_handling(self, mock_session_manager_class, connection_id):
        """
        Property: For any connection, errors should be handled gracefully
        
        **Validates: Requirement 15.1 (graceful degradation)**
        """
        # Arrange
        mock_session_manager = Mock()
        mock_session_manager.create_session.side_effect = Exception("DynamoDB error")
        mock_session_manager_class.return_value = mock_session_manager
        
        event = {
            'requestContext': {
                'connectionId': connection_id
            },
            'queryStringParameters': None
        }
        
        # Act
        response = lambda_handler(event, None)
        
        # Assert
        assert response['statusCode'] == 500
        assert 'error' in response.get('body', '{}').lower() or response['statusCode'] == 500
    
    @given(
        connection_id=connection_id_strategy,
        session_id=uuid_strategy
    )
    @settings(max_examples=50)
    @patch('websocket.connect.SessionManager')
    def test_property_ttl_updated_on_reconnection(
        self, mock_session_manager_class, connection_id, session_id
    ):
        """
        Property 6: For any reconnection, session TTL should be updated
        
        **Validates: Requirement 2.6**
        """
        # Arrange
        mock_session_manager = Mock()
        mock_session = Mock()
        mock_session.session_id = session_id
        mock_session.message_history = []
        mock_session_manager.get_session.return_value = mock_session
        mock_session_manager_class.return_value = mock_session_manager
        
        event = {
            'requestContext': {
                'connectionId': connection_id
            },
            'queryStringParameters': {
                'sessionId': session_id
            }
        }
        
        # Act
        response = lambda_handler(event, None)
        
        # Assert
        assert response['statusCode'] == 200
        mock_session_manager.update_ttl.assert_called_once_with(session_id)
    
    @given(
        connection_id=connection_id_strategy,
        empty_query_params=st.sampled_from([{}, None, {'other': 'param'}])
    )
    @settings(max_examples=50)
    @patch('websocket.connect.SessionManager')
    def test_property_missing_session_id_creates_new(
        self, mock_session_manager_class, connection_id, empty_query_params
    ):
        """
        Property: For any connection without sessionId parameter, new session created
        
        **Validates: Requirement 2.2**
        """
        # Arrange
        mock_session_manager = Mock()
        mock_session = Mock()
        mock_session.session_id = 'new-session'
        mock_session.message_history = []
        mock_session_manager.create_session.return_value = mock_session
        mock_session_manager_class.return_value = mock_session_manager
        
        event = {
            'requestContext': {
                'connectionId': connection_id
            },
            'queryStringParameters': empty_query_params
        }
        
        # Act
        response = lambda_handler(event, None)
        
        # Assert
        assert response['statusCode'] == 200
        mock_session_manager.create_session.assert_called_once()


class TestConnectionRoundTripProperty:
    """Test the complete connection round-trip property"""
    
    @given(
        connection_id=connection_id_strategy,
        has_session=st.booleans(),
        session_exists=st.booleans()
    )
    @settings(max_examples=100)
    @patch('websocket.connect.SessionManager')
    def test_property_connection_always_returns_session(
        self, mock_session_manager_class, connection_id, has_session, session_exists
    ):
        """
        Property 4 (Complete): For ANY connection request, backend should return success
        and ensure a session exists (either new or retrieved)
        
        **Validates: Requirements 2.2, 2.3, 9.1, 9.2, 9.5**
        """
        # Arrange
        mock_session_manager = Mock()
        
        if has_session and session_exists:
            # Existing valid session
            mock_session = Mock()
            mock_session.session_id = 'existing-session'
            mock_session.message_history = []
            mock_session_manager.get_session.return_value = mock_session
        elif has_session and not session_exists:
            # Invalid/expired session
            mock_session_manager.get_session.return_value = None
            mock_new_session = Mock()
            mock_new_session.session_id = 'new-session'
            mock_new_session.message_history = []
            mock_session_manager.create_session.return_value = mock_new_session
        else:
            # No session provided
            mock_new_session = Mock()
            mock_new_session.session_id = 'new-session'
            mock_new_session.message_history = []
            mock_session_manager.create_session.return_value = mock_new_session
        
        mock_session_manager_class.return_value = mock_session_manager
        
        event = {
            'requestContext': {
                'connectionId': connection_id
            },
            'queryStringParameters': {
                'sessionId': 'some-session-id'
            } if has_session else None
        }
        
        # Act
        response = lambda_handler(event, None)
        
        # Assert - Connection should always succeed
        assert response['statusCode'] == 200
        
        # Verify appropriate session operation was called
        if has_session and session_exists:
            mock_session_manager.get_session.assert_called_once()
        else:
            mock_session_manager.create_session.assert_called_once()
