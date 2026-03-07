"""
Unit tests for error scenarios in healthcare triage chatbot Lambda function.
Tests error handling for Bedrock failures, invalid inputs, and edge cases.
"""

import json
import pytest
from unittest.mock import patch, MagicMock
from botocore.exceptions import ClientError, ReadTimeoutError, ConnectTimeoutError
from lambda_function import lambda_handler


# Mock Lambda context for testing
class MockContext:
    def __init__(self, request_id='test-request-id'):
        self.request_id = request_id
        self.function_name = 'test-function'
        self.memory_limit_in_mb = 128
        self.invoked_function_arn = 'arn:aws:lambda:us-east-1:123456789012:function:test-function'
        self.aws_request_id = request_id


class TestBedrockServiceUnavailable:
    """Test handling of Bedrock service unavailability."""
    
    def test_bedrock_service_unavailable_exception(self):
        """Test that ServiceUnavailableException returns fallback response with MODERATE severity."""
        with patch('lambda_function.bedrock_runtime') as mock_bedrock:
            # Mock Bedrock to raise ServiceUnavailableException
            error_response = {
                'Error': {
                    'Code': 'ServiceUnavailableException',
                    'Message': 'Service is temporarily unavailable'
                }
            }
            mock_bedrock.invoke_model.side_effect = ClientError(error_response, 'invoke_model')
            
            # Create event with non-emergency symptoms
            event = {
                'body': json.dumps({'symptoms': 'mild headache'})
            }
            
            # Invoke Lambda handler
            response = lambda_handler(event, MockContext())
            
            # Verify response structure
            assert response['statusCode'] == 200, "Should return 200 for graceful degradation"
            
            body = json.loads(response['body'])
            
            # Verify fallback response
            assert body['severity'] == 'MODERATE', "Should return MODERATE severity for service unavailable"
            assert 'advice' in body
            assert 'unable to process' in body['advice'].lower() or 'seek in-person' in body['advice'].lower()
    
    def test_bedrock_throttling_exception(self):
        """Test that ThrottlingException returns fallback response."""
        with patch('lambda_function.bedrock_runtime') as mock_bedrock:
            # Mock Bedrock to raise ThrottlingException
            error_response = {
                'Error': {
                    'Code': 'ThrottlingException',
                    'Message': 'Rate exceeded'
                }
            }
            mock_bedrock.invoke_model.side_effect = ClientError(error_response, 'invoke_model')
            
            event = {
                'body': json.dumps({'symptoms': 'sore throat'})
            }
            
            response = lambda_handler(event, MockContext())
            
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            assert body['severity'] == 'MODERATE'
            assert 'advice' in body
    
    def test_bedrock_model_not_found(self):
        """Test that ResourceNotFoundException returns fallback response."""
        with patch('lambda_function.bedrock_runtime') as mock_bedrock:
            # Mock Bedrock to raise ResourceNotFoundException
            error_response = {
                'Error': {
                    'Code': 'ResourceNotFoundException',
                    'Message': 'Model not found'
                }
            }
            mock_bedrock.invoke_model.side_effect = ClientError(error_response, 'invoke_model')
            
            event = {
                'body': json.dumps({'symptoms': 'cough'})
            }
            
            response = lambda_handler(event, MockContext())
            
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            assert body['severity'] == 'MODERATE'
            assert 'advice' in body


class TestBedrockTimeout:
    """Test handling of Bedrock timeout scenarios."""
    
    def test_bedrock_read_timeout(self):
        """Test that ReadTimeoutError is handled gracefully."""
        with patch('lambda_function.bedrock_runtime') as mock_bedrock:
            # Mock Bedrock to raise ReadTimeoutError
            mock_bedrock.invoke_model.side_effect = ReadTimeoutError(
                endpoint_url='https://bedrock-runtime.us-east-1.amazonaws.com'
            )
            
            event = {
                'body': json.dumps({'symptoms': 'fatigue'})
            }
            
            response = lambda_handler(event, MockContext())
            
            # Verify graceful handling
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            assert body['severity'] == 'MODERATE'
            assert 'advice' in body
            assert len(body['advice']) > 0
    
    def test_bedrock_connect_timeout(self):
        """Test that ConnectTimeoutError is handled gracefully."""
        with patch('lambda_function.bedrock_runtime') as mock_bedrock:
            # Mock Bedrock to raise ConnectTimeoutError
            mock_bedrock.invoke_model.side_effect = ConnectTimeoutError(
                endpoint_url='https://bedrock-runtime.us-east-1.amazonaws.com'
            )
            
            event = {
                'body': json.dumps({'symptoms': 'dizziness'})
            }
            
            response = lambda_handler(event, MockContext())
            
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            assert body['severity'] == 'MODERATE'
            assert 'advice' in body


class TestInvalidInput:
    """Test handling of invalid input scenarios."""
    
    def test_empty_symptoms_string(self):
        """Test that empty symptoms string returns 400 error."""
        event = {
            'body': json.dumps({'symptoms': ''})
        }
        
        response = lambda_handler(event, MockContext())
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'error' in body
        assert 'required' in body['error'].lower()
    
    def test_whitespace_only_symptoms(self):
        """Test that whitespace-only symptoms are treated as empty."""
        event = {
            'body': json.dumps({'symptoms': '   \n\t  '})
        }
        
        response = lambda_handler(event, MockContext())
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'error' in body
    
    def test_missing_symptoms_field(self):
        """Test that missing symptoms field returns 400 error."""
        event = {
            'body': json.dumps({'other_field': 'value'})
        }
        
        response = lambda_handler(event, MockContext())
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'error' in body
        assert 'required' in body['error'].lower()
    
    def test_symptoms_exceeding_max_length(self):
        """Test that symptoms exceeding 2000 characters returns 400 error."""
        # Create a symptom string longer than 2000 characters
        long_symptoms = 'a' * 2001
        
        event = {
            'body': json.dumps({'symptoms': long_symptoms})
        }
        
        response = lambda_handler(event, MockContext())
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'error' in body
        assert '2000' in body['error']
    
    def test_symptoms_at_max_length_boundary(self):
        """Test that symptoms at exactly 2000 characters are accepted."""
        with patch('lambda_function.bedrock_runtime') as mock_bedrock:
            # Mock successful Bedrock response
            mock_response = {
                'body': MagicMock()
            }
            mock_response['body'].read.return_value = json.dumps({
                'output': {
                    'message': {
                        'content': [
                            {
                                'text': 'SEVERITY: LOW\nADVICE: Monitor your symptoms.'
                            }
                        ]
                    }
                }
            }).encode('utf-8')
            mock_bedrock.invoke_model.return_value = mock_response
            
            # Create symptoms at exactly 2000 characters
            symptoms_2000 = 'a' * 2000
            
            event = {
                'body': json.dumps({'symptoms': symptoms_2000})
            }
            
            response = lambda_handler(event, MockContext())
            
            # Should succeed
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            assert 'severity' in body
            assert 'advice' in body
    
    def test_malformed_json_body(self):
        """Test that malformed JSON returns 400 error."""
        event = {
            'body': 'not valid json {'
        }
        
        response = lambda_handler(event, MockContext())
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'error' in body
        assert 'json' in body['error'].lower()
    
    def test_empty_request_body(self):
        """Test that empty request body returns 400 error."""
        event = {
            'body': ''
        }
        
        response = lambda_handler(event, MockContext())
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'error' in body


class TestResponseParsingFailures:
    """Test handling of Bedrock response parsing failures."""
    
    def test_missing_output_field(self):
        """Test parsing when Bedrock response is missing 'output' field."""
        with patch('lambda_function.bedrock_runtime') as mock_bedrock:
            # Mock Bedrock response without expected structure
            mock_response = {
                'body': MagicMock()
            }
            mock_response['body'].read.return_value = json.dumps({
                'unexpected_field': 'value'
            }).encode('utf-8')
            mock_bedrock.invoke_model.return_value = mock_response
            
            event = {
                'body': json.dumps({'symptoms': 'headache'})
            }
            
            response = lambda_handler(event, MockContext())
            
            # Should return fallback response
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            assert body['severity'] == 'MODERATE'
            assert 'advice' in body
            assert len(body['advice']) > 0
    
    def test_missing_severity_in_response(self):
        """Test parsing when Bedrock response is missing SEVERITY label."""
        with patch('lambda_function.bedrock_runtime') as mock_bedrock:
            # Mock Bedrock response without SEVERITY label
            mock_response = {
                'body': MagicMock()
            }
            mock_response['body'].read.return_value = json.dumps({
                'output': {
                    'message': {
                        'content': [
                            {
                                'text': 'ADVICE: Rest and stay hydrated.'
                            }
                        ]
                    }
                }
            }).encode('utf-8')
            mock_bedrock.invoke_model.return_value = mock_response
            
            event = {
                'body': json.dumps({'symptoms': 'cough'})
            }
            
            response = lambda_handler(event, MockContext())
            
            # Should default to MODERATE severity
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            assert body['severity'] == 'MODERATE'
            assert 'advice' in body
    
    def test_missing_advice_in_response(self):
        """Test parsing when Bedrock response is missing ADVICE label."""
        with patch('lambda_function.bedrock_runtime') as mock_bedrock:
            # Mock Bedrock response without ADVICE label
            mock_response = {
                'body': MagicMock()
            }
            mock_response['body'].read.return_value = json.dumps({
                'output': {
                    'message': {
                        'content': [
                            {
                                'text': 'SEVERITY: LOW'
                            }
                        ]
                    }
                }
            }).encode('utf-8')
            mock_bedrock.invoke_model.return_value = mock_response
            
            event = {
                'body': json.dumps({'symptoms': 'runny nose'})
            }
            
            response = lambda_handler(event, MockContext())
            
            # Should provide fallback advice
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            assert body['severity'] == 'LOW'
            assert 'advice' in body
            assert len(body['advice']) > 0
            assert 'healthcare provider' in body['advice'].lower() or 'consult' in body['advice'].lower()
    
    def test_invalid_severity_value(self):
        """Test parsing when Bedrock returns invalid severity value."""
        with patch('lambda_function.bedrock_runtime') as mock_bedrock:
            # Mock Bedrock response with invalid severity
            mock_response = {
                'body': MagicMock()
            }
            mock_response['body'].read.return_value = json.dumps({
                'output': {
                    'message': {
                        'content': [
                            {
                                'text': 'SEVERITY: CRITICAL\nADVICE: Seek immediate care.'
                            }
                        ]
                    }
                }
            }).encode('utf-8')
            mock_bedrock.invoke_model.return_value = mock_response
            
            event = {
                'body': json.dumps({'symptoms': 'fever'})
            }
            
            response = lambda_handler(event, MockContext())
            
            # Should default to MODERATE for invalid severity
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            assert body['severity'] == 'MODERATE'
            assert 'advice' in body
    
    def test_empty_response_text(self):
        """Test parsing when Bedrock returns empty text."""
        with patch('lambda_function.bedrock_runtime') as mock_bedrock:
            # Mock Bedrock response with empty text
            mock_response = {
                'body': MagicMock()
            }
            mock_response['body'].read.return_value = json.dumps({
                'output': {
                    'message': {
                        'content': [
                            {
                                'text': ''
                            }
                        ]
                    }
                }
            }).encode('utf-8')
            mock_bedrock.invoke_model.return_value = mock_response
            
            event = {
                'body': json.dumps({'symptoms': 'nausea'})
            }
            
            response = lambda_handler(event, MockContext())
            
            # Should return fallback response
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            assert body['severity'] == 'MODERATE'
            assert 'advice' in body
            assert len(body['advice']) > 0
    
    def test_malformed_json_in_bedrock_response(self):
        """Test handling when Bedrock returns malformed JSON."""
        with patch('lambda_function.bedrock_runtime') as mock_bedrock:
            # Mock Bedrock response with invalid JSON
            mock_response = {
                'body': MagicMock()
            }
            mock_response['body'].read.return_value = b'not valid json {'
            mock_bedrock.invoke_model.return_value = mock_response
            
            event = {
                'body': json.dumps({'symptoms': 'back pain'})
            }
            
            response = lambda_handler(event, MockContext())
            
            # Should return fallback response
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            assert body['severity'] == 'MODERATE'
            assert 'advice' in body


class TestIAMPermissionDenied:
    """Test handling of IAM permission denied scenarios."""
    
    def test_access_denied_exception(self):
        """Test that AccessDeniedException returns fallback response."""
        with patch('lambda_function.bedrock_runtime') as mock_bedrock:
            # Mock Bedrock to raise AccessDeniedException
            error_response = {
                'Error': {
                    'Code': 'AccessDeniedException',
                    'Message': 'User is not authorized to perform: bedrock:InvokeModel'
                }
            }
            mock_bedrock.invoke_model.side_effect = ClientError(error_response, 'invoke_model')
            
            event = {
                'body': json.dumps({'symptoms': 'joint pain'})
            }
            
            response = lambda_handler(event, MockContext())
            
            # Should return fallback response with 200 status (graceful degradation)
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            assert body['severity'] == 'MODERATE'
            assert 'advice' in body
            assert 'unable to process' in body['advice'].lower() or 'seek in-person' in body['advice'].lower()
    
    def test_unauthorized_exception(self):
        """Test that UnauthorizedException returns fallback response."""
        with patch('lambda_function.bedrock_runtime') as mock_bedrock:
            # Mock Bedrock to raise UnauthorizedException
            error_response = {
                'Error': {
                    'Code': 'UnauthorizedException',
                    'Message': 'The security token included in the request is invalid'
                }
            }
            mock_bedrock.invoke_model.side_effect = ClientError(error_response, 'invoke_model')
            
            event = {
                'body': json.dumps({'symptoms': 'muscle aches'})
            }
            
            response = lambda_handler(event, MockContext())
            
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            assert body['severity'] == 'MODERATE'
            assert 'advice' in body
    
    def test_no_credentials_exposed_in_error(self):
        """Test that IAM errors don't expose credentials in response."""
        with patch('lambda_function.bedrock_runtime') as mock_bedrock:
            # Mock Bedrock to raise AccessDeniedException with detailed message
            error_response = {
                'Error': {
                    'Code': 'AccessDeniedException',
                    'Message': 'User: arn:aws:iam::123456789012:role/lambda-role is not authorized'
                }
            }
            mock_bedrock.invoke_model.side_effect = ClientError(error_response, 'invoke_model')
            
            event = {
                'body': json.dumps({'symptoms': 'rash'})
            }
            
            response = lambda_handler(event, MockContext())
            
            body = json.loads(response['body'])
            
            # Verify no AWS ARN or account ID in response
            body_str = json.dumps(body)
            assert 'arn:aws' not in body_str
            assert '123456789012' not in body_str
            assert 'lambda-role' not in body_str


class TestEdgeCases:
    """Test additional edge cases and error scenarios."""
    
    def test_special_characters_in_symptoms(self):
        """Test that special characters in symptoms are handled correctly."""
        with patch('lambda_function.bedrock_runtime') as mock_bedrock:
            mock_response = {
                'body': MagicMock()
            }
            mock_response['body'].read.return_value = json.dumps({
                'output': {
                    'message': {
                        'content': [
                            {
                                'text': 'SEVERITY: LOW\nADVICE: Monitor your symptoms.'
                            }
                        ]
                    }
                }
            }).encode('utf-8')
            mock_bedrock.invoke_model.return_value = mock_response
            
            # Test with special characters
            event = {
                'body': json.dumps({'symptoms': 'headache & nausea (mild) - started today'})
            }
            
            response = lambda_handler(event, MockContext())
            
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            assert 'severity' in body
            assert 'advice' in body
    
    def test_unicode_characters_in_symptoms(self):
        """Test that unicode characters in symptoms are handled correctly."""
        with patch('lambda_function.bedrock_runtime') as mock_bedrock:
            mock_response = {
                'body': MagicMock()
            }
            mock_response['body'].read.return_value = json.dumps({
                'output': {
                    'message': {
                        'content': [
                            {
                                'text': 'SEVERITY: LOW\nADVICE: Monitor your symptoms.'
                            }
                        ]
                    }
                }
            }).encode('utf-8')
            mock_bedrock.invoke_model.return_value = mock_response
            
            # Test with unicode characters
            event = {
                'body': json.dumps({'symptoms': 'douleur à la tête 头痛'})
            }
            
            response = lambda_handler(event, MockContext())
            
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            assert 'severity' in body
            assert 'advice' in body
    
    def test_generic_client_error(self):
        """Test handling of generic ClientError without specific code."""
        with patch('lambda_function.bedrock_runtime') as mock_bedrock:
            # Mock generic ClientError
            error_response = {
                'Error': {
                    'Code': 'UnknownError',
                    'Message': 'An unknown error occurred'
                }
            }
            mock_bedrock.invoke_model.side_effect = ClientError(error_response, 'invoke_model')
            
            event = {
                'body': json.dumps({'symptoms': 'stomach pain'})
            }
            
            response = lambda_handler(event, MockContext())
            
            # Should return fallback response
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            assert body['severity'] == 'MODERATE'
            assert 'advice' in body
    
    def test_unexpected_exception_in_handler(self):
        """Test that unexpected exceptions are caught and handled."""
        with patch('lambda_function.detect_emergency') as mock_detect:
            # Mock to raise unexpected exception
            mock_detect.side_effect = RuntimeError('Unexpected error')
            
            event = {
                'body': json.dumps({'symptoms': 'fever'})
            }
            
            response = lambda_handler(event, MockContext())
            
            # Should return 500 with fallback response
            assert response['statusCode'] == 500
            body = json.loads(response['body'])
            assert body['severity'] == 'MODERATE'
            assert 'advice' in body
