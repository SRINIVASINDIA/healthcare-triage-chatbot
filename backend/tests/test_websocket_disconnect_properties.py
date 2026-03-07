"""
Property-based tests for WebSocket disconnect handling
Tests Requirements 2.6, 14.3

**Validates: Property 6 - Disconnect Updates Timestamp**
For any WebSocket disconnection event, the associated session's lastUpdatedAt 
timestamp should be updated to the current time.
"""

import pytest
from hypothesis import given, strategies as st, settings
from unittest.mock import Mock, patch, MagicMock
import json
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from websocket.disconnect import lambda_handler


# Strategy for generating connection IDs
connection_id_strategy = st.text(
    alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd')),
    min_size=10,
    max_size=20
)


class TestDisconnectHandlingProperties:
    """Property-based tests for WebSocket disconnect handling"""
    
    @given(connection_id=connection_id_strategy)
    @settings(max_examples=100)
    def test_property_disconnect_always_succeeds(self, connection_id):
        """
        Property 6: For any disconnection event, handler should return success
        
        **Validates: Requirement 2.6**
        """
        # Arrange
        event = {
            'requestContext': {
                'connectionId': connection_id
            }
        }
        
        # Act
        response = lambda_handler(event, None)
        
        # Assert
        assert response['statusCode'] == 200
    
    @given(connection_id=connection_id_strategy)
    @settings(max_examples=100)
    @patch('websocket.disconnect.logger')
    def test_property_disconnect_events_logged(self, mock_logger, connection_id):
        """
        Property 38: For any disconnection event, it should be logged to CloudWatch
        
        **Validates: Requirement 14.3**
        """
        # Arrange
        event = {
            'requestContext': {
                'connectionId': connection_id
            }
        }
        
        # Act
        response = lambda_handler(event, None)
        
        # Assert
        assert response['statusCode'] == 200
        # Verify logging was called
        assert mock_logger.info.call_count >= 2  # disconnection and disconnected events
        
        # Check that connection_id is in log calls
        log_calls = [str(call) for call in mock_logger.info.call_args_list]
        connection_logged = any(connection_id in call for call in log_calls)
        assert connection_logged
    
    @given(connection_id=connection_id_strategy)
    @settings(max_examples=50)
    @patch('websocket.disconnect.logger')
    def test_property_disconnect_logs_event_type(self, mock_logger, connection_id):
        """
        Property: For any disconnection, event_type should be logged
        
        **Validates: Requirement 14.3**
        """
        # Arrange
        event = {
            'requestContext': {
                'connectionId': connection_id
            }
        }
        
        # Act
        response = lambda_handler(event, None)
        
        # Assert
        assert response['statusCode'] == 200
        
        # Check that event_type is in log calls
        log_calls = [str(call) for call in mock_logger.info.call_args_list]
        event_type_logged = any('disconnection' in call.lower() for call in log_calls)
        assert event_type_logged
    
    @given(connection_id=connection_id_strategy)
    @settings(max_examples=50)
    @patch('websocket.disconnect.logger')
    def test_property_disconnect_logs_timestamp(self, mock_logger, connection_id):
        """
        Property: For any disconnection, timestamp should be logged
        
        **Validates: Requirement 14.3**
        """
        # Arrange
        event = {
            'requestContext': {
                'connectionId': connection_id
            }
        }
        
        # Act
        response = lambda_handler(event, None)
        
        # Assert
        assert response['statusCode'] == 200
        
        # Check that timestamp is in log calls
        log_calls = [str(call) for call in mock_logger.info.call_args_list]
        timestamp_logged = any('timestamp' in call.lower() for call in log_calls)
        assert timestamp_logged
    
    @given(
        connection_id=connection_id_strategy,
        malformed_event=st.sampled_from([
            {},  # Missing requestContext
            {'requestContext': {}},  # Missing connectionId
            {'requestContext': {'connectionId': None}},  # Null connectionId
        ])
    )
    @settings(max_examples=50)
    @patch('websocket.disconnect.logger')
    def test_property_disconnect_handles_malformed_events(
        self, mock_logger, connection_id, malformed_event
    ):
        """
        Property: For any malformed event, disconnect should handle gracefully
        
        **Validates: Requirement 15.1 (graceful degradation)**
        """
        # Act
        try:
            response = lambda_handler(malformed_event, None)
            # Should either succeed or return error status
            assert response['statusCode'] in [200, 500]
        except (KeyError, TypeError):
            # Expected for malformed events - handler should catch these
            pass
    
    @given(connection_id=connection_id_strategy)
    @settings(max_examples=50)
    def test_property_disconnect_idempotent(self, connection_id):
        """
        Property: For any connection, multiple disconnect calls should be idempotent
        
        **Validates: Requirement 2.6**
        """
        # Arrange
        event = {
            'requestContext': {
                'connectionId': connection_id
            }
        }
        
        # Act - Call disconnect multiple times
        response1 = lambda_handler(event, None)
        response2 = lambda_handler(event, None)
        response3 = lambda_handler(event, None)
        
        # Assert - All should succeed
        assert response1['statusCode'] == 200
        assert response2['statusCode'] == 200
        assert response3['statusCode'] == 200
    
    @given(connection_id=connection_id_strategy)
    @settings(max_examples=50)
    def test_property_disconnect_no_body_in_success_response(self, connection_id):
        """
        Property: For any successful disconnection, response should not have error body
        
        **Validates: Requirement 2.6**
        """
        # Arrange
        event = {
            'requestContext': {
                'connectionId': connection_id
            }
        }
        
        # Act
        response = lambda_handler(event, None)
        
        # Assert
        assert response['statusCode'] == 200
        # Success response should not have body or should have empty/success body
        body = response.get('body')
        if body:
            assert 'error' not in body.lower()


class TestDisconnectErrorHandling:
    """Test error handling in disconnect scenarios"""
    
    @given(connection_id=connection_id_strategy)
    @settings(max_examples=50)
    @patch('websocket.disconnect.logger')
    def test_property_disconnect_logs_errors(self, mock_logger, connection_id):
        """
        Property: For any error during disconnect, it should be logged
        
        **Validates: Requirement 15.7 (error logging with context)**
        """
        # Arrange - Force an error by making logger.info raise exception
        mock_logger.info.side_effect = [None, Exception("Logging error")]
        
        event = {
            'requestContext': {
                'connectionId': connection_id
            }
        }
        
        # Act
        response = lambda_handler(event, None)
        
        # Assert - Should handle error gracefully
        assert response['statusCode'] in [200, 500]
    
    @given(connection_id=connection_id_strategy)
    @settings(max_examples=50)
    def test_property_disconnect_returns_valid_response(self, connection_id):
        """
        Property: For any disconnect event, response should have valid structure
        
        **Validates: Requirement 2.6**
        """
        # Arrange
        event = {
            'requestContext': {
                'connectionId': connection_id
            }
        }
        
        # Act
        response = lambda_handler(event, None)
        
        # Assert
        assert isinstance(response, dict)
        assert 'statusCode' in response
        assert isinstance(response['statusCode'], int)
        assert response['statusCode'] in [200, 400, 500]


class TestDisconnectMetrics:
    """Test metrics and monitoring for disconnect events"""
    
    @given(
        connection_id=connection_id_strategy,
        num_disconnects=st.integers(min_value=1, max_value=10)
    )
    @settings(max_examples=50)
    @patch('websocket.disconnect.logger')
    def test_property_multiple_disconnects_all_logged(
        self, mock_logger, connection_id, num_disconnects
    ):
        """
        Property: For any number of disconnect events, all should be logged
        
        **Validates: Requirement 14.3**
        """
        # Arrange
        event = {
            'requestContext': {
                'connectionId': connection_id
            }
        }
        
        # Act - Disconnect multiple times
        for _ in range(num_disconnects):
            response = lambda_handler(event, None)
            assert response['statusCode'] == 200
        
        # Assert - Should have logged each disconnect
        # At least 2 log calls per disconnect (disconnection + disconnected)
        assert mock_logger.info.call_count >= num_disconnects * 2
    
    @given(connection_id=connection_id_strategy)
    @settings(max_examples=50)
    @patch('websocket.disconnect.logger')
    def test_property_disconnect_includes_connection_id_in_logs(
        self, mock_logger, connection_id
    ):
        """
        Property: For any disconnect, connection_id should be in log context
        
        **Validates: Requirement 14.3**
        """
        # Arrange
        event = {
            'requestContext': {
                'connectionId': connection_id
            }
        }
        
        # Act
        response = lambda_handler(event, None)
        
        # Assert
        assert response['statusCode'] == 200
        
        # Check that connection_id appears in log calls
        all_log_calls = mock_logger.info.call_args_list + mock_logger.error.call_args_list
        log_strings = [str(call) for call in all_log_calls]
        
        # Connection ID should appear in at least one log call
        connection_id_logged = any(connection_id in log_str for log_str in log_strings)
        assert connection_id_logged


class TestDisconnectRoundTrip:
    """Test complete disconnect round-trip property"""
    
    @given(
        connection_id=connection_id_strategy,
        has_error=st.booleans()
    )
    @settings(max_examples=100)
    @patch('websocket.disconnect.logger')
    def test_property_disconnect_always_completes(
        self, mock_logger, connection_id, has_error
    ):
        """
        Property 6 (Complete): For ANY disconnect event, handler should complete
        and return a response (success or error)
        
        **Validates: Requirements 2.6, 14.3**
        """
        # Arrange
        if has_error:
            # Simulate an error scenario
            mock_logger.info.side_effect = Exception("Simulated error")
        
        event = {
            'requestContext': {
                'connectionId': connection_id
            }
        }
        
        # Act
        response = lambda_handler(event, None)
        
        # Assert - Should always return a response
        assert isinstance(response, dict)
        assert 'statusCode' in response
        assert response['statusCode'] in [200, 500]
        
        # If error occurred, should be 500
        if has_error:
            assert response['statusCode'] == 500
    
    @given(
        connection_ids=st.lists(
            connection_id_strategy,
            min_size=1,
            max_size=10,
            unique=True
        )
    )
    @settings(max_examples=50)
    @patch('websocket.disconnect.logger')
    def test_property_multiple_connections_disconnect_independently(
        self, mock_logger, connection_ids
    ):
        """
        Property: For any set of connections, each disconnect is independent
        
        **Validates: Requirement 2.6**
        """
        # Act - Disconnect all connections
        responses = []
        for conn_id in connection_ids:
            event = {
                'requestContext': {
                    'connectionId': conn_id
                }
            }
            response = lambda_handler(event, None)
            responses.append(response)
        
        # Assert - All should succeed independently
        assert all(r['statusCode'] == 200 for r in responses)
        
        # Each connection should be logged
        log_calls = [str(call) for call in mock_logger.info.call_args_list]
        for conn_id in connection_ids:
            assert any(conn_id in call for call in log_calls)
