"""
Property-based tests for WebSocket message processing
Tests Requirements 2.4, 2.5, 3.1, 4.1, 6.1, 15.1, 15.2, 15.3

**Validates: Property 5 - Message Processing Generates Response**
For any valid message sent through WebSocket, the backend should process it 
and send a response back to the client through the connection.
"""

import pytest
from hypothesis import given, strategies as st, settings, assume, HealthCheck
from unittest.mock import Mock, patch, MagicMock
import json
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Mock spacy and related modules before importing
mock_spacy = Mock()
mock_spacy.language = Mock()
mock_spacy.language.Language = Mock()
sys.modules['spacy'] = mock_spacy
sys.modules['spacy.language'] = mock_spacy.language

from websocket.message import lambda_handler
from core.models import ConversationSession, ConversationState, Message, MessageRole


# Strategies
uuid_strategy = st.uuids().map(str)
connection_id_strategy = st.text(
    alphabet='abcdefghijklmnopqrstuvwxyz0123456789',
    min_size=10,
    max_size=15
)
message_content_strategy = st.text(min_size=1, max_size=100).filter(lambda x: x.strip() != '')
domain_name_strategy = st.just('test.execute-api.us-east-1.amazonaws.com')
stage_strategy = st.sampled_from(['prod', 'dev'])


class TestMessageProcessingProperties:
    """Property-based tests for message processing"""
    
    @given(
        connection_id=connection_id_strategy,
        session_id=uuid_strategy,
        message=message_content_strategy,
        domain_name=domain_name_strategy,
        stage=stage_strategy
    )
    @settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
    @patch('websocket.message.boto3.client')
    @patch('websocket.message.SessionManager')
    @patch('websocket.message.MedicalNERClient')
    @patch('websocket.message.GroqClient')
    @patch('websocket.message.WebSocketClient')
    def test_property_valid_message_generates_response(
        self,
        mock_ws_client_class,
        mock_groq_class,
        mock_ner_class,
        mock_session_manager_class,
        mock_boto_client,
        connection_id,
        session_id,
        message,
        domain_name,
        stage
    ):
        """
        Property 5: For any valid message, backend should process and send response
        
        **Validates: Requirements 2.4, 2.5**
        """
        # Arrange
        mock_session_manager = Mock()
        mock_session = Mock()
        mock_session.session_id = session_id
        mock_session.message_history = []
        mock_session.conversation_state = ConversationState.INITIAL
        mock_session.follow_up_count = 0
        mock_session.emergency_detected = False
        mock_session_manager.get_session.return_value = mock_session
        mock_session_manager_class.return_value = mock_session_manager
        
        mock_ner = Mock()
        mock_ner.extract_entities.return_value = []
        mock_ner_class.return_value = mock_ner
        
        mock_groq = Mock()
        mock_groq.generate_response.return_value = "This is a test response"
        mock_groq_class.return_value = mock_groq
        
        mock_ws_client = Mock()
        mock_ws_client_class.return_value = mock_ws_client
        
        event = {
            'requestContext': {
                'connectionId': connection_id,
                'domainName': domain_name,
                'stage': stage
            },
            'body': json.dumps({
                'action': 'sendMessage',
                'sessionId': session_id,
                'message': message
            })
        }
        
        # Act
        response = lambda_handler(event, None)
        
        # Assert
        assert response['statusCode'] == 200
        mock_ws_client.send_message.assert_called_once()
        mock_session_manager.append_message.assert_called()
    
    @given(
        connection_id=connection_id_strategy,
        session_id=uuid_strategy,
        domain_name=domain_name_strategy,
        stage=stage_strategy
    )
    @settings(max_examples=50)
    @patch('websocket.message.boto3.client')
    @patch('websocket.message.WebSocketClient')
    def test_property_empty_message_rejected(
        self,
        mock_ws_client_class,
        mock_boto_client,
        connection_id,
        session_id,
        domain_name,
        stage
    ):
        """
        Property: For any empty message, backend should reject with error
        
        **Validates: Requirement 2.4 (validation)**
        """
        # Arrange
        mock_ws_client = Mock()
        mock_ws_client_class.return_value = mock_ws_client
        
        event = {
            'requestContext': {
                'connectionId': connection_id,
                'domainName': domain_name,
                'stage': stage
            },
            'body': json.dumps({
                'action': 'sendMessage',
                'sessionId': session_id,
                'message': ''
            })
        }
        
        # Act
        response = lambda_handler(event, None)
        
        # Assert
        assert response['statusCode'] == 400
        mock_ws_client.send_error.assert_called_once()
    
    @given(
        connection_id=connection_id_strategy,
        session_id=uuid_strategy,
        message=message_content_strategy,
        domain_name=domain_name_strategy,
        stage=stage_strategy
    )
    @settings(max_examples=50)
    @patch('websocket.message.boto3.client')
    @patch('websocket.message.SessionManager')
    @patch('websocket.message.WebSocketClient')
    def test_property_invalid_session_rejected(
        self,
        mock_ws_client_class,
        mock_session_manager_class,
        mock_boto_client,
        connection_id,
        session_id,
        message,
        domain_name,
        stage
    ):
        """
        Property: For any message with invalid session, backend should reject
        
        **Validates: Requirement 2.4**
        """
        # Arrange
        mock_session_manager = Mock()
        mock_session_manager.get_session.return_value = None  # Session not found
        mock_session_manager_class.return_value = mock_session_manager
        
        mock_ws_client = Mock()
        mock_ws_client_class.return_value = mock_ws_client
        
        event = {
            'requestContext': {
                'connectionId': connection_id,
                'domainName': domain_name,
                'stage': stage
            },
            'body': json.dumps({
                'action': 'sendMessage',
                'sessionId': session_id,
                'message': message
            })
        }
        
        # Act
        response = lambda_handler(event, None)
        
        # Assert
        assert response['statusCode'] == 404
        mock_ws_client.send_error.assert_called_once()
    
    @given(
        connection_id=connection_id_strategy,
        session_id=uuid_strategy,
        message=message_content_strategy,
        domain_name=domain_name_strategy,
        stage=stage_strategy
    )
    @settings(max_examples=50)
    @patch('websocket.message.boto3.client')
    @patch('websocket.message.SessionManager')
    @patch('websocket.message.MedicalNERClient')
    @patch('websocket.message.GroqClient')
    @patch('websocket.message.WebSocketClient')
    def test_property_message_appended_to_history(
        self,
        mock_ws_client_class,
        mock_groq_class,
        mock_ner_class,
        mock_session_manager_class,
        mock_boto_client,
        connection_id,
        session_id,
        message,
        domain_name,
        stage
    ):
        """
        Property 3: For any message, it should be appended to message history
        
        **Validates: Requirements 1.5, 3.1**
        """
        # Arrange
        mock_session_manager = Mock()
        mock_session = Mock()
        mock_session.session_id = session_id
        mock_session.message_history = []
        mock_session.conversation_state = ConversationState.INITIAL
        mock_session.follow_up_count = 0
        mock_session.emergency_detected = False
        mock_session_manager.get_session.return_value = mock_session
        mock_session_manager_class.return_value = mock_session_manager
        
        mock_ner = Mock()
        mock_ner.extract_entities.return_value = []
        mock_ner_class.return_value = mock_ner
        
        mock_groq = Mock()
        mock_groq.generate_response.return_value = "Response"
        mock_groq_class.return_value = mock_groq
        
        mock_ws_client = Mock()
        mock_ws_client_class.return_value = mock_ws_client
        
        event = {
            'requestContext': {
                'connectionId': connection_id,
                'domainName': domain_name,
                'stage': stage
            },
            'body': json.dumps({
                'action': 'sendMessage',
                'sessionId': session_id,
                'message': message
            })
        }
        
        # Act
        response = lambda_handler(event, None)
        
        # Assert
        assert response['statusCode'] == 200
        # Should append user message and assistant message
        assert mock_session_manager.append_message.call_count == 2
    
    @given(
        connection_id=connection_id_strategy,
        session_id=uuid_strategy,
        message=message_content_strategy,
        domain_name=domain_name_strategy,
        stage=stage_strategy
    )
    @settings(max_examples=50)
    @patch('websocket.message.boto3.client')
    @patch('websocket.message.SessionManager')
    @patch('websocket.message.MedicalNERClient')
    @patch('websocket.message.GroqClient')
    @patch('websocket.message.WebSocketClient')
    def test_property_ner_invoked_for_messages(
        self,
        mock_ws_client_class,
        mock_groq_class,
        mock_ner_class,
        mock_session_manager_class,
        mock_boto_client,
        connection_id,
        session_id,
        message,
        domain_name,
        stage
    ):
        """
        Property 11: For any message, Comprehend Medical (NER) should be invoked
        
        **Validates: Requirement 4.1**
        """
        # Arrange
        mock_session_manager = Mock()
        mock_session = Mock()
        mock_session.session_id = session_id
        mock_session.message_history = []
        mock_session.conversation_state = ConversationState.INITIAL
        mock_session.follow_up_count = 0
        mock_session.emergency_detected = False
        mock_session_manager.get_session.return_value = mock_session
        mock_session_manager_class.return_value = mock_session_manager
        
        mock_ner = Mock()
        mock_ner.extract_entities.return_value = []
        mock_ner_class.return_value = mock_ner
        
        mock_groq = Mock()
        mock_groq.generate_response.return_value = "Response"
        mock_groq_class.return_value = mock_groq
        
        mock_ws_client = Mock()
        mock_ws_client_class.return_value = mock_ws_client
        
        event = {
            'requestContext': {
                'connectionId': connection_id,
                'domainName': domain_name,
                'stage': stage
            },
            'body': json.dumps({
                'action': 'sendMessage',
                'sessionId': session_id,
                'message': message
            })
        }
        
        # Act
        response = lambda_handler(event, None)
        
        # Assert
        assert response['statusCode'] == 200
        mock_ner.extract_entities.assert_called_once_with(message)
    
    @given(
        connection_id=connection_id_strategy,
        session_id=uuid_strategy,
        message=message_content_strategy,
        domain_name=domain_name_strategy,
        stage=stage_strategy
    )
    @settings(max_examples=50)
    @patch('websocket.message.boto3.client')
    @patch('websocket.message.SessionManager')
    @patch('websocket.message.MedicalNERClient')
    @patch('websocket.message.GroqClient')
    @patch('websocket.message.WebSocketClient')
    def test_property_ner_failure_continues_processing(
        self,
        mock_ws_client_class,
        mock_groq_class,
        mock_ner_class,
        mock_session_manager_class,
        mock_boto_client,
        connection_id,
        session_id,
        message,
        domain_name,
        stage
    ):
        """
        Property 13: For any message, if NER fails, processing should continue
        
        **Validates: Requirements 4.6, 15.2 (graceful degradation)**
        """
        # Arrange
        mock_session_manager = Mock()
        mock_session = Mock()
        mock_session.session_id = session_id
        mock_session.message_history = []
        mock_session.conversation_state = ConversationState.INITIAL
        mock_session.follow_up_count = 0
        mock_session.emergency_detected = False
        mock_session_manager.get_session.return_value = mock_session
        mock_session_manager_class.return_value = mock_session_manager
        
        mock_ner = Mock()
        mock_ner.extract_entities.side_effect = Exception("NER service unavailable")
        mock_ner_class.return_value = mock_ner
        
        mock_groq = Mock()
        mock_groq.generate_response.return_value = "Response"
        mock_groq_class.return_value = mock_groq
        
        mock_ws_client = Mock()
        mock_ws_client_class.return_value = mock_ws_client
        
        event = {
            'requestContext': {
                'connectionId': connection_id,
                'domainName': domain_name,
                'stage': stage
            },
            'body': json.dumps({
                'action': 'sendMessage',
                'sessionId': session_id,
                'message': message
            })
        }
        
        # Act
        response = lambda_handler(event, None)
        
        # Assert - Should still succeed
        assert response['statusCode'] == 200
        mock_ws_client.send_message.assert_called_once()
    
    @given(
        connection_id=connection_id_strategy,
        session_id=uuid_strategy,
        message=message_content_strategy,
        domain_name=domain_name_strategy,
        stage=stage_strategy
    )
    @settings(max_examples=50)
    @patch('websocket.message.boto3.client')
    @patch('websocket.message.SessionManager')
    @patch('websocket.message.MedicalNERClient')
    @patch('websocket.message.GroqClient')
    @patch('websocket.message.WebSocketClient')
    def test_property_ai_failure_returns_fallback(
        self,
        mock_ws_client_class,
        mock_groq_class,
        mock_ner_class,
        mock_session_manager_class,
        mock_boto_client,
        connection_id,
        session_id,
        message,
        domain_name,
        stage
    ):
        """
        Property 40: For any message, if AI fails, fallback response should be sent
        
        **Validates: Requirement 15.3**
        """
        # Arrange
        mock_session_manager = Mock()
        mock_session = Mock()
        mock_session.session_id = session_id
        mock_session.message_history = []
        mock_session.conversation_state = ConversationState.INITIAL
        mock_session.follow_up_count = 0
        mock_session.emergency_detected = False
        mock_session_manager.get_session.return_value = mock_session
        mock_session_manager_class.return_value = mock_session_manager
        
        mock_ner = Mock()
        mock_ner.extract_entities.return_value = []
        mock_ner_class.return_value = mock_ner
        
        mock_groq = Mock()
        mock_groq.generate_response.side_effect = Exception("AI service unavailable")
        mock_groq._get_fallback_response.return_value = "Fallback response"
        mock_groq_class.return_value = mock_groq
        
        mock_ws_client = Mock()
        mock_ws_client_class.return_value = mock_ws_client
        
        event = {
            'requestContext': {
                'connectionId': connection_id,
                'domainName': domain_name,
                'stage': stage
            },
            'body': json.dumps({
                'action': 'sendMessage',
                'sessionId': session_id,
                'message': message
            })
        }
        
        # Act
        response = lambda_handler(event, None)
        
        # Assert - Should still succeed with fallback
        assert response['statusCode'] == 200
        mock_ws_client.send_message.assert_called_once()
    
    @given(
        connection_id=connection_id_strategy,
        session_id=uuid_strategy,
        emergency_message=st.sampled_from([
            "I have chest pain",
            "I can't breathe",
            "I'm having a stroke",
            "severe chest pain",
            "difficulty breathing"
        ]),
        domain_name=domain_name_strategy,
        stage=stage_strategy
    )
    @settings(max_examples=50)
    @patch('websocket.message.boto3.client')
    @patch('websocket.message.SessionManager')
    @patch('websocket.message.MedicalNERClient')
    @patch('websocket.message.EmergencyDetector')
    @patch('websocket.message.GroqClient')
    @patch('websocket.message.WebSocketClient')
    def test_property_emergency_detected_and_flagged(
        self,
        mock_ws_client_class,
        mock_groq_class,
        mock_emergency_detector_class,
        mock_ner_class,
        mock_session_manager_class,
        mock_boto_client,
        connection_id,
        session_id,
        emergency_message,
        domain_name,
        stage
    ):
        """
        Property 18: For any message with emergency keywords, emergency should be detected
        
        **Validates: Requirements 6.1, 6.2**
        """
        # Arrange
        mock_session_manager = Mock()
        mock_session = Mock()
        mock_session.session_id = session_id
        mock_session.message_history = []
        mock_session.conversation_state = ConversationState.INITIAL
        mock_session.follow_up_count = 0
        mock_session.emergency_detected = False
        mock_session_manager.get_session.return_value = mock_session
        mock_session_manager_class.return_value = mock_session_manager
        
        mock_ner = Mock()
        mock_ner.extract_entities.return_value = []
        mock_ner_class.return_value = mock_ner
        
        mock_emergency_detector = Mock()
        mock_emergency_detector.detect_emergency.return_value = True
        mock_emergency_detector_class.return_value = mock_emergency_detector
        
        mock_groq = Mock()
        mock_groq.generate_response.return_value = "Call 911 immediately"
        mock_groq_class.return_value = mock_groq
        
        mock_ws_client = Mock()
        mock_ws_client_class.return_value = mock_ws_client
        
        event = {
            'requestContext': {
                'connectionId': connection_id,
                'domainName': domain_name,
                'stage': stage
            },
            'body': json.dumps({
                'action': 'sendMessage',
                'sessionId': session_id,
                'message': emergency_message
            })
        }
        
        # Act
        response = lambda_handler(event, None)
        
        # Assert
        assert response['statusCode'] == 200
        mock_emergency_detector.detect_emergency.assert_called_once()
        # Session should be updated with emergency flag
        mock_session_manager.update_session.assert_called()


class TestMessageValidation:
    """Test message validation properties"""
    
    @given(
        connection_id=connection_id_strategy,
        domain_name=domain_name_strategy,
        stage=stage_strategy,
        invalid_action=st.text(min_size=1, max_size=20).filter(lambda x: x != 'sendMessage')
    )
    @settings(max_examples=50)
    @patch('websocket.message.boto3.client')
    @patch('websocket.message.WebSocketClient')
    def test_property_invalid_action_rejected(
        self,
        mock_ws_client_class,
        mock_boto_client,
        connection_id,
        domain_name,
        stage,
        invalid_action
    ):
        """
        Property: For any invalid action, request should be rejected
        
        **Validates: Requirement 2.4**
        """
        # Arrange
        mock_ws_client = Mock()
        mock_ws_client_class.return_value = mock_ws_client
        
        event = {
            'requestContext': {
                'connectionId': connection_id,
                'domainName': domain_name,
                'stage': stage
            },
            'body': json.dumps({
                'action': invalid_action,
                'sessionId': 'test-session',
                'message': 'test message'
            })
        }
        
        # Act
        response = lambda_handler(event, None)
        
        # Assert
        assert response['statusCode'] == 400
        mock_ws_client.send_error.assert_called_once()
    
    @given(
        connection_id=connection_id_strategy,
        message=message_content_strategy,
        domain_name=domain_name_strategy,
        stage=stage_strategy
    )
    @settings(max_examples=50)
    @patch('websocket.message.boto3.client')
    @patch('websocket.message.WebSocketClient')
    def test_property_missing_session_id_rejected(
        self,
        mock_ws_client_class,
        mock_boto_client,
        connection_id,
        message,
        domain_name,
        stage
    ):
        """
        Property: For any message without sessionId, request should be rejected
        
        **Validates: Requirement 2.4**
        """
        # Arrange
        mock_ws_client = Mock()
        mock_ws_client_class.return_value = mock_ws_client
        
        event = {
            'requestContext': {
                'connectionId': connection_id,
                'domainName': domain_name,
                'stage': stage
            },
            'body': json.dumps({
                'action': 'sendMessage',
                'message': message
            })
        }
        
        # Act
        response = lambda_handler(event, None)
        
        # Assert
        assert response['statusCode'] == 400
        mock_ws_client.send_error.assert_called_once()
    
    @given(
        connection_id=connection_id_strategy,
        domain_name=domain_name_strategy,
        stage=stage_strategy
    )
    @settings(max_examples=50)
    @patch('websocket.message.boto3.client')
    @patch('websocket.message.WebSocketClient')
    def test_property_malformed_json_rejected(
        self,
        mock_ws_client_class,
        mock_boto_client,
        connection_id,
        domain_name,
        stage
    ):
        """
        Property: For any malformed JSON, request should be rejected
        
        **Validates: Requirement 2.4**
        """
        # Arrange
        mock_ws_client = Mock()
        mock_ws_client_class.return_value = mock_ws_client
        
        event = {
            'requestContext': {
                'connectionId': connection_id,
                'domainName': domain_name,
                'stage': stage
            },
            'body': 'invalid json {'
        }
        
        # Act
        response = lambda_handler(event, None)
        
        # Assert
        assert response['statusCode'] == 400
        mock_ws_client.send_error.assert_called_once()
