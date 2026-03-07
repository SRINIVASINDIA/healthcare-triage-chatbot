"""
Unit tests for validation and security features in healthcare triage chatbot.
Tests input validation, error responses, and sensitive data protection.
"""

import json
import pytest
from unittest.mock import patch, MagicMock
from lambda_function import lambda_handler, sanitize_response_data


# Mock Lambda context for testing
class MockContext:
    def __init__(self, request_id='test-request-id'):
        self.request_id = request_id
        self.function_name = 'test-function'
        self.memory_limit_in_mb = 128
        self.invoked_function_arn = 'arn:aws:lambda:us-east-1:123456789012:function:test-function'
        self.aws_request_id = request_id


class TestInputValidation:
    """Test input validation for triage requests."""
    
    def test_missing_symptoms_field_returns_400(self):
        """Test that missing symptoms field returns 400 status."""
        event = {
            'body': json.dumps({'other_field': 'value'})
        }
        
        response = lambda_handler(event, MockContext())
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'error' in body
        assert 'symptoms field is required' in body['error']
    
    def test_empty_symptoms_returns_400(self):
        """Test that empty symptoms string returns 400 status."""
        event = {
            'body': json.dumps({'symptoms': ''})
        }
        
        response = lambda_handler(event, MockContext())
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'error' in body
        assert 'required' in body['error'].lower()
    
    def test_whitespace_only_symptoms_returns_400(self):
        """Test that whitespace-only symptoms are treated as empty."""
        event = {
            'body': json.dumps({'symptoms': '   \n\t  '})
        }
        
        response = lambda_handler(event, MockContext())
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'error' in body
    
    def test_symptoms_exceeding_2000_chars_returns_400(self):
        """Test that symptoms exceeding 2000 characters returns 400 status."""
        long_symptoms = 'a' * 2001
        
        event = {
            'body': json.dumps({'symptoms': long_symptoms})
        }
        
        response = lambda_handler(event, MockContext())
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'error' in body
        assert '2000' in body['error']


class TestErrorResponses:
    """Test error response handling and graceful degradation."""
    
    def test_parsing_failure_returns_200_with_fallback(self):
        """Test that parsing failures return 200 with fallback advice (graceful degradation)."""
        with patch('lambda_function.bedrock_runtime') as mock_bedrock:
            # Mock Bedrock response with unparseable format
            mock_response = {
                'body': MagicMock()
            }
            mock_response['body'].read.return_value = json.dumps({
                'output': {
                    'message': {
                        'content': [
                            {
                                'text': 'Random text without proper format'
                            }
                        ]
                    }
                }
            }).encode('utf-8')
            mock_bedrock.invoke_model.return_value = mock_response
            
            event = {
                'body': json.dumps({'symptoms': 'headache'})
            }
            
            response = lambda_handler(event, MockContext())
            
            # Should return 200 for graceful degradation
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            assert body['severity'] == 'MODERATE'
            assert 'advice' in body
            assert len(body['advice']) > 0
    
    def test_malformed_json_returns_400(self):
        """Test that malformed JSON in request returns 400 status."""
        event = {
            'body': 'not valid json {'
        }
        
        response = lambda_handler(event, MockContext())
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'error' in body
        assert 'json' in body['error'].lower()


class TestSensitiveDataProtection:
    """Test that sensitive data is not exposed in responses."""
    
    def test_sanitize_response_data_detects_aws_access_key(self):
        """Test that AWS access key patterns are detected and sanitized."""
        sensitive_text = "Error: aws_access_key_id is invalid"
        
        result = sanitize_response_data(sensitive_text)
        
        assert result == "An error occurred. Please try again or contact support."
    
    def test_sanitize_response_data_detects_akia_prefix(self):
        """Test that AKIA prefix (AWS access key) is detected."""
        sensitive_text = "Error with AKIAIOSFODNN7EXAMPLE"
        
        result = sanitize_response_data(sensitive_text)
        
        assert result == "An error occurred. Please try again or contact support."
    
    def test_sanitize_response_data_detects_secret(self):
        """Test that 'secret' keyword is detected."""
        sensitive_text = "Error: secret key not found"
        
        result = sanitize_response_data(sensitive_text)
        
        assert result == "An error occurred. Please try again or contact support."
    
    def test_sanitize_response_data_detects_password(self):
        """Test that 'password' keyword is detected."""
        sensitive_text = "Error: password authentication failed"
        
        result = sanitize_response_data(sensitive_text)
        
        assert result == "An error occurred. Please try again or contact support."
    
    def test_sanitize_response_data_detects_token(self):
        """Test that 'token' keyword is detected."""
        sensitive_text = "Error: session token expired"
        
        result = sanitize_response_data(sensitive_text)
        
        assert result == "An error occurred. Please try again or contact support."
    
    def test_sanitize_response_data_detects_credential(self):
        """Test that 'credential' keyword is detected."""
        sensitive_text = "Error: credential validation failed"
        
        result = sanitize_response_data(sensitive_text)
        
        assert result == "An error occurred. Please try again or contact support."
    
    def test_sanitize_response_data_case_insensitive(self):
        """Test that detection is case-insensitive."""
        sensitive_text = "Error: AWS_SECRET_ACCESS_KEY not set"
        
        result = sanitize_response_data(sensitive_text)
        
        assert result == "An error occurred. Please try again or contact support."
    
    def test_sanitize_response_data_allows_safe_text(self):
        """Test that safe text passes through unchanged."""
        safe_text = "Invalid request: symptoms field is required"
        
        result = sanitize_response_data(safe_text)
        
        assert result == safe_text
    
    def test_no_credentials_in_success_response(self):
        """Test that successful responses don't contain sensitive data."""
        with patch('lambda_function.bedrock_runtime') as mock_bedrock:
            mock_response = {
                'body': MagicMock()
            }
            mock_response['body'].read.return_value = json.dumps({
                'output': {
                    'message': {
                        'content': [
                            {
                                'text': 'SEVERITY: LOW\nADVICE: Rest and stay hydrated.'
                            }
                        ]
                    }
                }
            }).encode('utf-8')
            mock_bedrock.invoke_model.return_value = mock_response
            
            event = {
                'body': json.dumps({'symptoms': 'mild headache'})
            }
            
            response = lambda_handler(event, MockContext())
            
            body_str = json.dumps(response['body'])
            
            # Check for common sensitive patterns
            assert 'aws_access_key' not in body_str.lower()
            assert 'aws_secret' not in body_str.lower()
            assert 'akia' not in body_str.lower()
            assert 'arn:aws' not in body_str
    
    def test_no_credentials_in_error_response(self):
        """Test that error responses don't contain sensitive data."""
        event = {
            'body': json.dumps({'symptoms': ''})
        }
        
        response = lambda_handler(event, MockContext())
        
        body_str = json.dumps(response['body'])
        
        # Check for common sensitive patterns
        assert 'aws_access_key' not in body_str.lower()
        assert 'aws_secret' not in body_str.lower()
        assert 'akia' not in body_str.lower()
        assert 'password' not in body_str.lower()
        assert 'token' not in body_str.lower()


class TestCloudWatchLogging:
    """Test that errors are logged to CloudWatch."""
    
    @patch('lambda_function.logger')
    def test_missing_symptoms_logged(self, mock_logger):
        """Test that missing symptoms validation error is logged."""
        event = {
            'body': json.dumps({'symptoms': ''})
        }
        
        lambda_handler(event, MockContext())
        
        # Verify warning was logged
        mock_logger.warning.assert_called()
        call_args = str(mock_logger.warning.call_args)
        assert 'Missing symptoms' in call_args or 'symptoms field' in call_args
    
    @patch('lambda_function.logger')
    def test_bedrock_error_logged(self, mock_logger):
        """Test that Bedrock errors are logged to CloudWatch."""
        with patch('lambda_function.bedrock_runtime') as mock_bedrock:
            from botocore.exceptions import ClientError
            
            error_response = {
                'Error': {
                    'Code': 'ServiceException',
                    'Message': 'Service unavailable'
                }
            }
            mock_bedrock.invoke_model.side_effect = ClientError(error_response, 'invoke_model')
            
            event = {
                'body': json.dumps({'symptoms': 'headache'})
            }
            
            lambda_handler(event, MockContext())
            
            # Verify error was logged
            mock_logger.error.assert_called()
            call_args = str(mock_logger.error.call_args)
            assert 'Bedrock' in call_args or 'ServiceException' in call_args
    
    @patch('lambda_function.logger')
    def test_json_decode_error_logged(self, mock_logger):
        """Test that JSON decode errors are logged."""
        event = {
            'body': 'not valid json {'
        }
        
        lambda_handler(event, MockContext())
        
        # Verify error was logged
        mock_logger.error.assert_called()
        call_args = str(mock_logger.error.call_args)
        assert 'JSON' in call_args or 'decode' in call_args


class TestGracefulDegradation:
    """Test graceful degradation for various failure scenarios."""
    
    def test_bedrock_unavailable_returns_200_with_fallback(self):
        """Test that Bedrock unavailability returns 200 with fallback advice."""
        with patch('lambda_function.bedrock_runtime') as mock_bedrock:
            from botocore.exceptions import ClientError
            
            error_response = {
                'Error': {
                    'Code': 'ServiceUnavailableException',
                    'Message': 'Service temporarily unavailable'
                }
            }
            mock_bedrock.invoke_model.side_effect = ClientError(error_response, 'invoke_model')
            
            event = {
                'body': json.dumps({'symptoms': 'cough'})
            }
            
            response = lambda_handler(event, MockContext())
            
            # Should return 200 for graceful degradation
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            assert body['severity'] == 'MODERATE'
            assert 'advice' in body
            assert 'unable to process' in body['advice'].lower() or 'seek in-person' in body['advice'].lower()
    
    def test_response_parsing_failure_returns_200_with_fallback(self):
        """Test that response parsing failures return 200 with fallback."""
        with patch('lambda_function.bedrock_runtime') as mock_bedrock:
            mock_response = {
                'body': MagicMock()
            }
            # Return completely invalid response
            mock_response['body'].read.return_value = b'invalid response'
            mock_bedrock.invoke_model.return_value = mock_response
            
            event = {
                'body': json.dumps({'symptoms': 'fever'})
            }
            
            response = lambda_handler(event, MockContext())
            
            # Should return 200 with fallback
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            assert body['severity'] == 'MODERATE'
            assert 'advice' in body
            assert len(body['advice']) > 0
