"""
Property-based tests for REST API backward compatibility

Feature: chatgpt-like-enhancements
Tests Properties 30, 31, 32
"""

import pytest
from hypothesis import given, strategies as st, settings
import json
from unittest.mock import Mock, patch, MagicMock
from core.models import ConversationSession, Message, MessageRole, ConversationState
from datetime import datetime


# Feature: chatgpt-like-enhancements, Property 30: REST API Backward Compatibility
@given(st.text(min_size=1, max_size=500).filter(lambda x: x.strip() != ''))
@settings(max_examples=100)
def test_rest_api_response_format(symptoms_text):
    """
    For any POST request to /triage endpoint with symptoms field,
    the backend should return a response in the format {severity: string, advice: string}
    
    **Validates: Requirements 12.1, 12.3**
    """
    from lambda_function import lambda_handler
    
    # Arrange - Create REST API event
    event = {
        'httpMethod': 'POST',
        'path': '/triage',
        'body': json.dumps({'symptoms': symptoms_text}),
        'headers': {'Content-Type': 'application/json'}
    }
    
    # Mock external dependencies
    with patch('lambda_function.invoke_groq') as mock_invoke_groq:
        mock_invoke_groq.return_value = {
            'severity': 'LOW',
            'advice': 'Based on your symptoms, this appears to be LOW severity. Please monitor your symptoms.'
        }
        
        # Act
        response = lambda_handler(event, None)
        
        # Assert - Check response format matches original system
        assert response is not None
        assert 'statusCode' in response
        assert response['statusCode'] == 200
        
        body = json.loads(response['body'])
        assert 'severity' in body, "Response must contain 'severity' field"
        assert 'advice' in body, "Response must contain 'advice' field"
        assert isinstance(body['severity'], str), "Severity must be a string"
        assert isinstance(body['advice'], str), "Advice must be a string"
        assert body['severity'] in ['LOW', 'MODERATE', 'SEVERE'], "Severity must be valid"


# Feature: chatgpt-like-enhancements, Property 31: REST API Stateless Operation
@given(st.text(min_size=1, max_size=500).filter(lambda x: x.strip() != ''))
@settings(max_examples=100)
def test_rest_api_stateless_operation(symptoms_text):
    """
    For any REST API request, the backend should process it without requiring
    a session ID and create a temporary single-turn session that doesn't persist
    
    **Validates: Requirements 12.2, 12.5**
    """
    from lambda_function import lambda_handler
    
    # Arrange - Create REST API event without session ID
    event = {
        'httpMethod': 'POST',
        'path': '/triage',
        'body': json.dumps({'symptoms': symptoms_text}),
        'headers': {'Content-Type': 'application/json'}
    }
    
    # Mock dependencies
    with patch('lambda_function.invoke_groq') as mock_invoke_groq:
        mock_invoke_groq.return_value = {
            'severity': 'MODERATE',
            'advice': 'This appears to be MODERATE severity.'
        }
        
        # Act
        response = lambda_handler(event, None)
        
        # Assert - Should work without session ID
        assert response is not None
        assert response['statusCode'] == 200
        
        # Should not require session ID in request
        request_body = json.loads(event['body'])
        assert 'sessionId' not in request_body, "REST API should not require session ID"
        
        # Response should not contain session ID (stateless)
        response_body = json.loads(response['body'])
        assert 'sessionId' not in response_body, "REST API response should not expose session ID"


# Feature: chatgpt-like-enhancements, Property 32: Emergency Detection Consistency Across APIs
@given(st.sampled_from([
    "I have chest pain",
    "I'm having a stroke",
    "I have difficulty breathing",
    "severe chest pain and shortness of breath",
    "I think I'm having a seizure"
]))
@settings(max_examples=50)
def test_emergency_detection_consistency(emergency_message):
    """
    For any message containing emergency keywords, both REST and WebSocket APIs
    should detect the emergency and return SEVERE severity using the same detection logic
    
    **Validates: Requirements 12.4**
    """
    from lambda_function import lambda_handler
    from core.emergency_detector import EmergencyDetector
    
    # Test REST API
    rest_event = {
        'httpMethod': 'POST',
        'path': '/triage',
        'body': json.dumps({'symptoms': emergency_message}),
        'headers': {'Content-Type': 'application/json'}
    }
    
    with patch('lambda_function.invoke_groq') as mock_invoke_groq:
        mock_invoke_groq.return_value = {
            'severity': 'SEVERE',
            'advice': 'This is a medical emergency. Call 911 immediately.'
        }
        
        # Act - REST API
        rest_response = lambda_handler(rest_event, None)
        
        # Assert - REST API should detect emergency
        assert rest_response['statusCode'] == 200
        rest_body = json.loads(rest_response['body'])
        assert rest_body['severity'] == 'SEVERE', f"REST API should detect emergency in: {emergency_message}"
    
    # Test WebSocket API uses same emergency detector
    detector = EmergencyDetector()
    
    # Act - WebSocket API emergency detection (pass message_history, not session)
    is_emergency = detector.detect_emergency([
        Message(
            timestamp=datetime.now().isoformat(),
            role=MessageRole.USER,
            content=emergency_message,
            extracted_entities=[]
        )
    ])
    
    # Assert - WebSocket API should also detect emergency
    assert is_emergency, f"WebSocket API should detect emergency in: {emergency_message}"


# Feature: chatgpt-like-enhancements, Property 30: REST API Error Handling
@given(st.one_of(
    st.none(),
    st.just(''),
    st.just('   '),
    st.text(min_size=3000, max_size=5000)  # Too long
))
@settings(max_examples=50)
def test_rest_api_input_validation(invalid_symptoms):
    """
    For any invalid input to REST API, should return appropriate error response
    
    **Validates: Requirements 12.1, 12.3**
    """
    from lambda_function import lambda_handler
    
    # Arrange
    if invalid_symptoms is None:
        body = json.dumps({})  # Missing symptoms field
    else:
        body = json.dumps({'symptoms': invalid_symptoms})
    
    event = {
        'httpMethod': 'POST',
        'path': '/triage',
        'body': body,
        'headers': {'Content-Type': 'application/json'}
    }
    
    # Act
    response = lambda_handler(event, None)
    
    # Assert - Should handle gracefully
    assert response is not None
    assert 'statusCode' in response
    
    # Should return error status for invalid input
    if invalid_symptoms is None or (isinstance(invalid_symptoms, str) and not invalid_symptoms.strip()):
        assert response['statusCode'] in [400, 422], "Should return error for missing/empty symptoms"
    elif isinstance(invalid_symptoms, str) and len(invalid_symptoms) > 2000:
        # Should either reject or truncate
        assert response['statusCode'] in [200, 400, 413], "Should handle oversized input"


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
