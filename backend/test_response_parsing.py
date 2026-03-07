"""
Unit tests for response parsing and formatting
Tests Task 2.6: parse_bedrock_response and Lambda response formatting
"""

import json
import pytest
from unittest.mock import Mock
from lambda_function import parse_bedrock_response, lambda_handler, create_error_response


class TestParseBedrockResponse:
    """Test parse_bedrock_response function"""
    
    def test_parse_valid_response_low_severity(self):
        """Test parsing valid Bedrock response with LOW severity"""
        mock_response = {
            'body': Mock(read=lambda: json.dumps({
                'output': {
                    'message': {
                        'content': [{
                            'text': 'SEVERITY: LOW\nADVICE: Rest and drink plenty of fluids.'
                        }]
                    }
                }
            }).encode())
        }
        
        result = parse_bedrock_response(mock_response)
        
        assert result['severity'] == 'LOW'
        assert result['advice'] == 'Rest and drink plenty of fluids.'
    
    def test_parse_valid_response_moderate_severity(self):
        """Test parsing valid Bedrock response with MODERATE severity"""
        mock_response = {
            'body': Mock(read=lambda: json.dumps({
                'output': {
                    'message': {
                        'content': [{
                            'text': 'SEVERITY: MODERATE\nADVICE: Schedule an appointment with your doctor within 24-48 hours.'
                        }]
                    }
                }
            }).encode())
        }
        
        result = parse_bedrock_response(mock_response)
        
        assert result['severity'] == 'MODERATE'
        assert result['advice'] == 'Schedule an appointment with your doctor within 24-48 hours.'
    
    def test_parse_valid_response_severe_severity(self):
        """Test parsing valid Bedrock response with SEVERE severity"""
        mock_response = {
            'body': Mock(read=lambda: json.dumps({
                'output': {
                    'message': {
                        'content': [{
                            'text': 'SEVERITY: SEVERE\nADVICE: Seek immediate medical attention at an urgent care or emergency room.'
                        }]
                    }
                }
            }).encode())
        }
        
        result = parse_bedrock_response(mock_response)
        
        assert result['severity'] == 'SEVERE'
        assert result['advice'] == 'Seek immediate medical attention at an urgent care or emergency room.'
    
    def test_parse_response_with_lowercase_severity(self):
        """Test parsing response with lowercase severity (should be converted to uppercase)"""
        mock_response = {
            'body': Mock(read=lambda: json.dumps({
                'output': {
                    'message': {
                        'content': [{
                            'text': 'SEVERITY: low\nADVICE: Take over-the-counter pain medication.'
                        }]
                    }
                }
            }).encode())
        }
        
        result = parse_bedrock_response(mock_response)
        
        assert result['severity'] == 'LOW'
        assert result['advice'] == 'Take over-the-counter pain medication.'
    
    def test_parse_response_with_invalid_severity_defaults_to_moderate(self):
        """Test that invalid severity values default to MODERATE"""
        mock_response = {
            'body': Mock(read=lambda: json.dumps({
                'output': {
                    'message': {
                        'content': [{
                            'text': 'SEVERITY: CRITICAL\nADVICE: See a doctor.'
                        }]
                    }
                }
            }).encode())
        }
        
        result = parse_bedrock_response(mock_response)
        
        assert result['severity'] == 'MODERATE'
        assert result['advice'] == 'See a doctor.'
    
    def test_parse_response_missing_severity_defaults_to_moderate(self):
        """Test that missing severity defaults to MODERATE"""
        mock_response = {
            'body': Mock(read=lambda: json.dumps({
                'output': {
                    'message': {
                        'content': [{
                            'text': 'ADVICE: Consult with your healthcare provider.'
                        }]
                    }
                }
            }).encode())
        }
        
        result = parse_bedrock_response(mock_response)
        
        assert result['severity'] == 'MODERATE'
        assert result['advice'] == 'Consult with your healthcare provider.'
    
    def test_parse_response_missing_advice_uses_fallback(self):
        """Test that missing advice uses fallback message"""
        mock_response = {
            'body': Mock(read=lambda: json.dumps({
                'output': {
                    'message': {
                        'content': [{
                            'text': 'SEVERITY: LOW'
                        }]
                    }
                }
            }).encode())
        }
        
        result = parse_bedrock_response(mock_response)
        
        assert result['severity'] == 'LOW'
        assert result['advice'] == 'Please consult with a healthcare provider about your symptoms.'
    
    def test_parse_malformed_response_returns_fallback(self):
        """Test that malformed response returns fallback with MODERATE severity"""
        mock_response = {
            'body': Mock(read=lambda: json.dumps({
                'invalid': 'structure'
            }).encode())
        }
        
        result = parse_bedrock_response(mock_response)
        
        assert result['severity'] == 'MODERATE'
        assert result['advice'] == 'Please consult with a healthcare provider about your symptoms.'
    
    def test_parse_response_with_extra_whitespace(self):
        """Test parsing response with extra whitespace"""
        mock_response = {
            'body': Mock(read=lambda: json.dumps({
                'output': {
                    'message': {
                        'content': [{
                            'text': '  SEVERITY:   LOW  \n  ADVICE:   Rest and hydrate.  '
                        }]
                    }
                }
            }).encode())
        }
        
        result = parse_bedrock_response(mock_response)
        
        assert result['severity'] == 'LOW'
        assert result['advice'] == 'Rest and hydrate.'
    
    def test_parse_response_with_multiline_advice(self):
        """Test parsing response where advice spans multiple lines"""
        mock_response = {
            'body': Mock(read=lambda: json.dumps({
                'output': {
                    'message': {
                        'content': [{
                            'text': 'SEVERITY: MODERATE\nADVICE: Take over-the-counter pain medication and rest.\nIf symptoms worsen, see a doctor.'
                        }]
                    }
                }
            }).encode())
        }
        
        result = parse_bedrock_response(mock_response)
        
        assert result['severity'] == 'MODERATE'
        # Should capture first line of advice
        assert 'Take over-the-counter pain medication and rest.' in result['advice']


class TestLambdaResponseFormatting:
    """Test Lambda response formatting"""
    
    def test_successful_response_has_correct_structure(self):
        """Test that successful responses have statusCode, headers, and body"""
        event = {
            'body': json.dumps({'symptoms': 'headache'})
        }
        
        response = lambda_handler(event, {})
        
        assert 'statusCode' in response
        assert 'headers' in response
        assert 'body' in response
        assert response['statusCode'] == 200
    
    def test_successful_response_has_cors_headers(self):
        """Test that successful responses include CORS headers"""
        event = {
            'body': json.dumps({'symptoms': 'headache'})
        }
        
        response = lambda_handler(event, {})
        
        headers = response['headers']
        assert 'Access-Control-Allow-Origin' in headers
        assert headers['Access-Control-Allow-Origin'] == '*'
        assert 'Access-Control-Allow-Headers' in headers
        assert 'Content-Type' in headers['Access-Control-Allow-Headers']
        assert 'Access-Control-Allow-Methods' in headers
        assert 'POST' in headers['Access-Control-Allow-Methods']
    
    def test_successful_response_body_is_valid_json(self):
        """Test that response body is valid JSON"""
        event = {
            'body': json.dumps({'symptoms': 'chest pain'})
        }
        
        response = lambda_handler(event, {})
        
        # Should not raise exception
        body = json.loads(response['body'])
        assert isinstance(body, dict)
    
    def test_successful_response_body_contains_severity_and_advice(self):
        """Test that response body contains severity and advice fields"""
        event = {
            'body': json.dumps({'symptoms': 'chest pain'})
        }
        
        response = lambda_handler(event, {})
        body = json.loads(response['body'])
        
        assert 'severity' in body
        assert 'advice' in body
        assert body['severity'] in ['LOW', 'MODERATE', 'SEVERE']
        assert isinstance(body['advice'], str)
        assert len(body['advice']) > 0
    
    def test_error_response_has_correct_structure(self):
        """Test that error responses have correct structure"""
        event = {
            'body': json.dumps({'symptoms': ''})
        }
        
        response = lambda_handler(event, {})
        
        assert response['statusCode'] == 400
        assert 'headers' in response
        assert 'body' in response
    
    def test_error_response_has_cors_headers(self):
        """Test that error responses include CORS headers"""
        event = {
            'body': json.dumps({'symptoms': ''})
        }
        
        response = lambda_handler(event, {})
        
        headers = response['headers']
        assert 'Access-Control-Allow-Origin' in headers
        assert headers['Access-Control-Allow-Origin'] == '*'
    
    def test_error_response_body_is_valid_json(self):
        """Test that error response body is valid JSON"""
        event = {
            'body': json.dumps({'symptoms': ''})
        }
        
        response = lambda_handler(event, {})
        
        # Should not raise exception
        body = json.loads(response['body'])
        assert isinstance(body, dict)
        assert 'error' in body


class TestCreateErrorResponse:
    """Test create_error_response function"""
    
    def test_create_error_response_400(self):
        """Test creating 400 error response"""
        response = create_error_response(400, 'Bad request')
        
        assert response['statusCode'] == 400
        assert 'headers' in response
        assert 'body' in response
        body = json.loads(response['body'])
        assert body['error'] == 'Bad request'
    
    def test_create_error_response_500(self):
        """Test creating 500 error response"""
        response = create_error_response(500, 'Internal server error')
        
        assert response['statusCode'] == 500
        body = json.loads(response['body'])
        assert body['error'] == 'Internal server error'
    
    def test_error_response_has_cors_headers(self):
        """Test that error responses have CORS headers"""
        response = create_error_response(400, 'Test error')
        
        headers = response['headers']
        assert 'Access-Control-Allow-Origin' in headers
        assert headers['Access-Control-Allow-Origin'] == '*'
        assert 'Content-Type' in headers
        assert headers['Content-Type'] == 'application/json'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
