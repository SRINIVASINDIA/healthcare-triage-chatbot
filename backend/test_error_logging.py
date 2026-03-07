"""
Test CloudWatch logging for error scenarios.
Verifies that errors are logged with request IDs as required by task 3.1.
"""

import json
import pytest
from unittest.mock import patch, MagicMock
from botocore.exceptions import ClientError
from lambda_function import lambda_handler


class MockContext:
    """Mock Lambda context with request ID."""
    def __init__(self, request_id='test-request-123'):
        self.request_id = request_id
        self.function_name = 'test-function'
        self.memory_limit_in_mb = 128


class TestErrorLogging:
    """Test that errors are logged to CloudWatch with request IDs."""
    
    def test_bedrock_service_exception_logged_with_request_id(self, caplog):
        """Test that ServiceException is logged with request ID."""
        with patch('lambda_function.bedrock_runtime') as mock_bedrock:
            error_response = {
                'Error': {
                    'Code': 'ServiceException',
                    'Message': 'Service temporarily unavailable'
                }
            }
            mock_bedrock.invoke_model.side_effect = ClientError(error_response, 'invoke_model')
            
            event = {'body': json.dumps({'symptoms': 'headache'})}
            context = MockContext(request_id='req-12345')
            
            response = lambda_handler(event, context)
            
            # Verify response is fallback
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            assert body['severity'] == 'MODERATE'
            
            # Verify logging contains request ID
            log_messages = [record.message for record in caplog.records]
            assert any('req-12345' in msg for msg in log_messages), "Request ID should be in logs"
            assert any('ServiceException' in msg or 'service exception' in msg for msg in log_messages), "Error type should be logged"
    
    def test_resource_not_found_logged_with_request_id(self, caplog):
        """Test that ResourceNotFoundException is logged with request ID and model ID."""
        with patch('lambda_function.bedrock_runtime') as mock_bedrock:
            error_response = {
                'Error': {
                    'Code': 'ResourceNotFoundException',
                    'Message': 'Model not found'
                }
            }
            mock_bedrock.invoke_model.side_effect = ClientError(error_response, 'invoke_model')
            
            event = {'body': json.dumps({'symptoms': 'cough'})}
            context = MockContext(request_id='req-67890')
            
            response = lambda_handler(event, context)
            
            # Verify fallback response
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            assert body['severity'] == 'MODERATE'
            
            # Verify logging
            log_messages = [record.message for record in caplog.records]
            assert any('req-67890' in msg for msg in log_messages), "Request ID should be in logs"
            assert any('model not found' in msg.lower() or 'ResourceNotFoundException' in msg for msg in log_messages), "Model not found error should be logged"
    
    def test_timeout_error_logged_with_request_id(self, caplog):
        """Test that timeout errors are logged with request ID."""
        with patch('lambda_function.bedrock_runtime') as mock_bedrock:
            from botocore.exceptions import ReadTimeoutError
            mock_bedrock.invoke_model.side_effect = ReadTimeoutError(
                endpoint_url='https://bedrock-runtime.us-east-1.amazonaws.com'
            )
            
            event = {'body': json.dumps({'symptoms': 'fever'})}
            context = MockContext(request_id='req-timeout-001')
            
            response = lambda_handler(event, context)
            
            # Verify fallback response
            assert response['statusCode'] == 200
            
            # Verify logging
            log_messages = [record.message for record in caplog.records]
            assert any('req-timeout-001' in msg for msg in log_messages), "Request ID should be in logs"
            assert any('timeout' in msg.lower() or 'ReadTimeoutError' in msg for msg in log_messages), "Timeout error should be logged"
    
    def test_access_denied_logged_with_request_id(self, caplog):
        """Test that AccessDeniedException is logged with request ID."""
        with patch('lambda_function.bedrock_runtime') as mock_bedrock:
            error_response = {
                'Error': {
                    'Code': 'AccessDeniedException',
                    'Message': 'Not authorized to invoke model'
                }
            }
            mock_bedrock.invoke_model.side_effect = ClientError(error_response, 'invoke_model')
            
            event = {'body': json.dumps({'symptoms': 'sore throat'})}
            context = MockContext(request_id='req-access-denied')
            
            response = lambda_handler(event, context)
            
            # Verify fallback response
            assert response['statusCode'] == 200
            
            # Verify logging
            log_messages = [record.message for record in caplog.records]
            assert any('req-access-denied' in msg for msg in log_messages), "Request ID should be in logs"
            assert any('access denied' in msg.lower() or 'AccessDeniedException' in msg for msg in log_messages), "Access denied error should be logged"
    
    def test_invalid_input_logged_with_request_id(self, caplog):
        """Test that invalid input is logged with request ID."""
        event = {'body': json.dumps({'symptoms': ''})}
        context = MockContext(request_id='req-invalid-input')
        
        response = lambda_handler(event, context)
        
        # Verify error response
        assert response['statusCode'] == 400
        
        # Verify logging
        log_messages = [record.message for record in caplog.records]
        assert any('req-invalid-input' in msg for msg in log_messages), "Request ID should be in logs"
        assert any('missing' in msg.lower() or 'symptoms' in msg.lower() for msg in log_messages), "Missing symptoms should be logged"
    
    def test_emergency_detection_logged_with_request_id(self, caplog):
        """Test that emergency detection is logged with request ID."""
        event = {'body': json.dumps({'symptoms': 'chest pain'})}
        context = MockContext(request_id='req-emergency-123')
        
        response = lambda_handler(event, context)
        
        # Verify emergency response
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['severity'] == 'SEVERE'
        
        # Verify logging
        log_messages = [record.message for record in caplog.records]
        assert any('req-emergency-123' in msg for msg in log_messages), "Request ID should be in logs"
        assert any('emergency' in msg.lower() for msg in log_messages), "Emergency detection should be logged"
    
    def test_successful_bedrock_invocation_logged_with_request_id(self, caplog):
        """Test that successful Bedrock invocation is logged with request ID."""
        with patch('lambda_function.bedrock_runtime') as mock_bedrock:
            mock_response = {
                'body': MagicMock()
            }
            mock_response['body'].read.return_value = json.dumps({
                'output': {
                    'message': {
                        'content': [
                            {'text': 'SEVERITY: LOW\nADVICE: Rest and hydrate.'}
                        ]
                    }
                }
            }).encode('utf-8')
            mock_bedrock.invoke_model.return_value = mock_response
            
            event = {'body': json.dumps({'symptoms': 'mild headache'})}
            context = MockContext(request_id='req-success-456')
            
            response = lambda_handler(event, context)
            
            # Verify successful response
            assert response['statusCode'] == 200
            
            # Verify logging
            log_messages = [record.message for record in caplog.records]
            assert any('req-success-456' in msg for msg in log_messages), "Request ID should be in logs"
            assert any('bedrock' in msg.lower() for msg in log_messages), "Bedrock invocation should be logged"
