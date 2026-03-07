"""
Unit tests for Bedrock integration
Tests Task 4.2: Bedrock invocation, timeout handling, and error scenarios
"""

import json
import pytest
from unittest.mock import patch, MagicMock, Mock
from botocore.exceptions import ClientError
from lambda_function import (
    lambda_handler,
    invoke_bedrock,
    BEDROCK_MODEL_ID
)


class MockContext:
    """Mock Lambda context for testing"""
    def __init__(self, request_id='test-request-id'):
        self.request_id = request_id
        self.function_name = 'test-function'
        self.memory_limit_in_mb = 128


class TestBedrockSuccessfulInvocation:
    """Test successful Bedrock invocation - Requirements 2.1, 2.6, 10.1, 10.2"""
    
    @patch('lambda_function.bedrock_runtime')
    def test_bedrock_invoked_with_correct_model_id(self, mock_bedrock):
        """Test that Bedrock is invoked with correct model ID"""
        # Mock successful Bedrock response
        mock_response = {
            'body': Mock(read=lambda: json.dumps({
                'output': {
                    'message': {
                        'content': [{
                            'text': 'SEVERITY: LOW\nADVICE: Rest and hydrate.'
                        }]
                    }
                }
            }).encode())
        }
        mock_bedrock.invoke_model.return_value = mock_response
        
        event = {
            'body': json.dumps({'symptoms': 'mild headache'})
        }
        
        response = lambda_handler(event, MockContext())
        
        # Verify Bedrock was called
        assert mock_bedrock.invoke_model.called
        
        # Verify model ID
        call_args = mock_bedrock.invoke_model.call_args
        model_id = call_args.kwargs.get('modelId', call_args.args[0] if call_args.args else None)
        assert model_id == BEDROCK_MODEL_ID
    
    @patch('lambda_function.bedrock_runtime')
    def test_bedrock_invoked_with_correct_parameters(self, mock_bedrock):
        """Test that Bedrock is invoked with correct temperature and maxTokens"""
        mock_response = {
            'body': Mock(read=lambda: json.dumps({
                'output': {
                    'message': {
                        'content': [{
                            'text': 'SEVERITY: MODERATE\nADVICE: See a doctor.'
                        }]
                    }
                }
            }).encode())
        }
        mock_bedrock.invoke_model.return_value = mock_response
        
        event = {
            'body': json.dumps({'symptoms': 'persistent cough'})
        }
        
        response = lambda_handler(event, MockContext())
        
        # Get request body
        call_args = mock_bedrock.invoke_model.call_args
        body_json = call_args.kwargs.get('body', call_args.args[1] if len(call_args.args) > 1 else None)
        request_body = json.loads(body_json)
        
        # Verify inferenceConfig
        assert 'inferenceConfig' in request_body
        assert request_body['inferenceConfig']['temperature'] == 0.3
        assert request_body['inferenceConfig']['maxTokens'] == 500
    
    @patch('lambda_function.bedrock_runtime')
    def test_bedrock_receives_symptom_description(self, mock_bedrock):
        """Test that Bedrock receives the symptom description in the prompt"""
        mock_response = {
            'body': Mock(read=lambda: json.dumps({
                'output': {
                    'message': {
                        'content': [{
                            'text': 'SEVERITY: LOW\nADVICE: Rest.'
                        }]
                    }
                }
            }).encode())
        }
        mock_bedrock.invoke_model.return_value = mock_response
        
        symptoms = 'sore throat and runny nose'
        event = {
            'body': json.dumps({'symptoms': symptoms})
        }
        
        response = lambda_handler(event, MockContext())
        
        # Get request body
        call_args = mock_bedrock.invoke_model.call_args
        body_json = call_args.kwargs.get('body', call_args.args[1] if len(call_args.args) > 1 else None)
        request_body = json.loads(body_json)
        
        # Verify symptoms are in the prompt
        prompt = request_body['messages'][0]['content']
        assert symptoms in prompt
    
    @patch('lambda_function.bedrock_runtime')
    def test_successful_invocation_returns_200(self, mock_bedrock):
        """Test that successful Bedrock invocation returns 200 status"""
        mock_response = {
            'body': Mock(read=lambda: json.dumps({
                'output': {
                    'message': {
                        'content': [{
                            'text': 'SEVERITY: LOW\nADVICE: Monitor symptoms.'
                        }]
                    }
                }
            }).encode())
        }
        mock_bedrock.invoke_model.return_value = mock_response
        
        event = {
            'body': json.dumps({'symptoms': 'mild fever'})
        }
        
        response = lambda_handler(event, MockContext())
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert 'severity' in body
        assert 'advice' in body


class TestBedrockTimeoutHandling:
    """Test Bedrock timeout handling - Requirements 2.6, 10.1, 10.2"""
    
    @patch('lambda_function.bedrock_runtime')
    def test_bedrock_timeout_returns_fallback(self, mock_bedrock):
        """Test that Bedrock timeout returns fallback response"""
        # Simulate timeout exception
        mock_bedrock.invoke_model.side_effect = Exception('Timeout')
        
        event = {
            'body': json.dumps({'symptoms': 'headache'})
        }
        
        response = lambda_handler(event, MockContext())
        
        # Should return 200 with fallback advice (graceful degradation)
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['severity'] == 'MODERATE'
        assert 'unable to process' in body['advice'].lower() or 'seek in-person' in body['advice'].lower()
    
    @patch('lambda_function.bedrock_runtime')
    def test_timeout_exception_handled_gracefully(self, mock_bedrock):
        """Test that timeout exceptions are handled gracefully"""
        mock_bedrock.invoke_model.side_effect = TimeoutError('Request timed out')
        
        event = {
            'body': json.dumps({'symptoms': 'cough'})
        }
        
        response = lambda_handler(event, MockContext())
        
        # Should not raise exception
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert 'severity' in body
        assert 'advice' in body


class TestBedrockServiceUnavailable:
    """Test Bedrock service unavailable scenarios - Requirements 2.6, 10.1, 10.2"""
    
    @patch('lambda_function.bedrock_runtime')
    def test_service_exception_returns_fallback(self, mock_bedrock):
        """Test that ServiceException returns fallback response"""
        # Simulate ServiceException
        error_response = {
            'Error': {
                'Code': 'ServiceException',
                'Message': 'Service temporarily unavailable'
            }
        }
        mock_bedrock.invoke_model.side_effect = ClientError(error_response, 'invoke_model')
        
        event = {
            'body': json.dumps({'symptoms': 'fatigue'})
        }
        
        response = lambda_handler(event, MockContext())
        
        # Should return 200 with fallback advice
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['severity'] == 'MODERATE'
        assert 'unable to process' in body['advice'].lower() or 'seek in-person' in body['advice'].lower()
    
    @patch('lambda_function.bedrock_runtime')
    def test_throttling_exception_returns_fallback(self, mock_bedrock):
        """Test that ThrottlingException returns fallback response"""
        error_response = {
            'Error': {
                'Code': 'ThrottlingException',
                'Message': 'Rate exceeded'
            }
        }
        mock_bedrock.invoke_model.side_effect = ClientError(error_response, 'invoke_model')
        
        event = {
            'body': json.dumps({'symptoms': 'nausea'})
        }
        
        response = lambda_handler(event, MockContext())
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['severity'] == 'MODERATE'
    
    @patch('lambda_function.bedrock_runtime')
    def test_service_unavailable_logs_error(self, mock_bedrock):
        """Test that service unavailable errors are logged"""
        error_response = {
            'Error': {
                'Code': 'ServiceException',
                'Message': 'Service unavailable'
            }
        }
        mock_bedrock.invoke_model.side_effect = ClientError(error_response, 'invoke_model')
        
        with patch('lambda_function.logger') as mock_logger:
            event = {
                'body': json.dumps({'symptoms': 'dizziness'})
            }
            
            response = lambda_handler(event, MockContext())
            
            # Verify error was logged
            assert mock_logger.error.called


class TestBedrockModelNotFound:
    """Test Bedrock model not found error - Requirements 2.6, 10.1, 10.2"""
    
    @patch('lambda_function.bedrock_runtime')
    def test_model_not_found_returns_fallback(self, mock_bedrock):
        """Test that ResourceNotFoundException returns fallback response"""
        error_response = {
            'Error': {
                'Code': 'ResourceNotFoundException',
                'Message': 'Model not found'
            }
        }
        mock_bedrock.invoke_model.side_effect = ClientError(error_response, 'invoke_model')
        
        event = {
            'body': json.dumps({'symptoms': 'back pain'})
        }
        
        response = lambda_handler(event, MockContext())
        
        # Should return 200 with fallback advice
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['severity'] == 'MODERATE'
        assert 'unable to process' in body['advice'].lower() or 'seek in-person' in body['advice'].lower()
    
    @patch('lambda_function.bedrock_runtime')
    def test_model_not_found_logs_error(self, mock_bedrock):
        """Test that model not found errors are logged"""
        error_response = {
            'Error': {
                'Code': 'ResourceNotFoundException',
                'Message': 'Model amazon.nova-v2 not found'
            }
        }
        mock_bedrock.invoke_model.side_effect = ClientError(error_response, 'invoke_model')
        
        with patch('lambda_function.logger') as mock_logger:
            event = {
                'body': json.dumps({'symptoms': 'joint pain'})
            }
            
            response = lambda_handler(event, MockContext())
            
            # Verify error was logged with model info
            assert mock_logger.error.called
            error_call = str(mock_logger.error.call_args)
            assert 'model not found' in error_call.lower() or 'ResourceNotFoundException' in error_call


class TestBedrockAccessDenied:
    """Test Bedrock access denied scenarios - Requirements 2.6, 10.1, 10.2"""
    
    @patch('lambda_function.bedrock_runtime')
    def test_access_denied_returns_fallback(self, mock_bedrock):
        """Test that AccessDeniedException returns fallback response"""
        error_response = {
            'Error': {
                'Code': 'AccessDeniedException',
                'Message': 'User is not authorized to perform: bedrock:InvokeModel'
            }
        }
        mock_bedrock.invoke_model.side_effect = ClientError(error_response, 'invoke_model')
        
        event = {
            'body': json.dumps({'symptoms': 'muscle aches'})
        }
        
        response = lambda_handler(event, MockContext())
        
        # Should return 200 with fallback advice
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['severity'] == 'MODERATE'
    
    @patch('lambda_function.bedrock_runtime')
    def test_access_denied_logs_error(self, mock_bedrock):
        """Test that access denied errors are logged"""
        error_response = {
            'Error': {
                'Code': 'AccessDeniedException',
                'Message': 'Access denied'
            }
        }
        mock_bedrock.invoke_model.side_effect = ClientError(error_response, 'invoke_model')
        
        with patch('lambda_function.logger') as mock_logger:
            event = {
                'body': json.dumps({'symptoms': 'rash'})
            }
            
            response = lambda_handler(event, MockContext())
            
            # Verify error was logged
            assert mock_logger.error.called


class TestBedrockInvokeDirect:
    """Test invoke_bedrock function directly"""
    
    @patch('lambda_function.bedrock_runtime')
    def test_invoke_bedrock_returns_triage_response(self, mock_bedrock):
        """Test that invoke_bedrock returns proper triage response structure"""
        mock_response = {
            'body': Mock(read=lambda: json.dumps({
                'output': {
                    'message': {
                        'content': [{
                            'text': 'SEVERITY: LOW\nADVICE: Rest and monitor.'
                        }]
                    }
                }
            }).encode())
        }
        mock_bedrock.invoke_model.return_value = mock_response
        
        result = invoke_bedrock('headache', 'test-request-id')
        
        assert 'severity' in result
        assert 'advice' in result
        assert result['severity'] in ['LOW', 'MODERATE', 'SEVERE']
    
    @patch('lambda_function.bedrock_runtime')
    def test_invoke_bedrock_handles_client_error(self, mock_bedrock):
        """Test that invoke_bedrock handles ClientError gracefully"""
        error_response = {
            'Error': {
                'Code': 'ServiceException',
                'Message': 'Service error'
            }
        }
        mock_bedrock.invoke_model.side_effect = ClientError(error_response, 'invoke_model')
        
        result = invoke_bedrock('symptoms', 'test-request-id')
        
        # Should return fallback response
        assert result['severity'] == 'MODERATE'
        assert 'unable to process' in result['advice'].lower() or 'seek in-person' in result['advice'].lower()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
