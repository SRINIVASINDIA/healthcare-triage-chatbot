"""
Unit tests for Groq API client
Tests Requirements 14.2, 15.3
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import requests
import time
from backend.integrations.groq_client import GroqClient


class TestGroqClientInitialization:
    """Test Groq client initialization"""
    
    def test_init_with_defaults(self):
        """Test initialization with default model"""
        client = GroqClient(api_key='test-key')
        assert client.api_key == 'test-key'
        assert client.model == 'llama-3.1-8b-instant'
    
    def test_init_with_custom_model(self):
        """Test initialization with custom model"""
        client = GroqClient(api_key='test-key', model='custom-model')
        assert client.api_key == 'test-key'
        assert client.model == 'custom-model'


class TestGroqClientGenerateResponse:
    """Test response generation"""
    
    @patch('backend.integrations.groq_client.requests.post')
    def test_successful_response(self, mock_post):
        """Test successful API response"""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'choices': [
                {
                    'message': {
                        'content': 'This is a test response'
                    }
                }
            ],
            'usage': {
                'prompt_tokens': 10,
                'completion_tokens': 5,
                'total_tokens': 15
            }
        }
        mock_post.return_value = mock_response
        
        client = GroqClient(api_key='test-key')
        
        # Act
        result = client.generate_response('test prompt')
        
        # Assert
        assert result == 'This is a test response'
        mock_post.assert_called_once()
        
        # Verify request structure
        call_args = mock_post.call_args
        assert call_args[0][0] == GroqClient.GROQ_API_URL
        assert call_args[1]['headers']['Authorization'] == 'Bearer test-key'
        assert call_args[1]['json']['model'] == 'llama-3.1-8b-instant'
        assert call_args[1]['json']['messages'][0]['content'] == 'test prompt'
    
    @patch('backend.integrations.groq_client.requests.post')
    def test_custom_temperature_and_max_tokens(self, mock_post):
        """Test custom temperature and max_tokens parameters"""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'choices': [{'message': {'content': 'response'}}],
            'usage': {}
        }
        mock_post.return_value = mock_response
        
        client = GroqClient(api_key='test-key')
        
        # Act
        client.generate_response('test', temperature=0.7, max_tokens=1000)
        
        # Assert
        call_args = mock_post.call_args
        assert call_args[1]['json']['temperature'] == 0.7
        assert call_args[1]['json']['max_tokens'] == 1000
    
    @patch('backend.integrations.groq_client.requests.post')
    def test_default_temperature_and_max_tokens(self, mock_post):
        """Test default temperature and max_tokens are used"""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'choices': [{'message': {'content': 'response'}}],
            'usage': {}
        }
        mock_post.return_value = mock_response
        
        client = GroqClient(api_key='test-key')
        
        # Act
        client.generate_response('test')
        
        # Assert
        call_args = mock_post.call_args
        assert call_args[1]['json']['temperature'] == 0.3
        assert call_args[1]['json']['max_tokens'] == 500
    
    @patch('backend.integrations.groq_client.requests.post')
    def test_timeout_returns_fallback(self, mock_post):
        """Test timeout returns fallback response (Requirement 15.3)"""
        # Arrange
        mock_post.side_effect = requests.exceptions.Timeout()
        client = GroqClient(api_key='test-key')
        
        # Act
        result = client.generate_response('test')
        
        # Assert
        assert 'unable to process your request' in result.lower()
        assert 'technical issue' in result.lower()
        assert '911' in result
    
    @patch('backend.integrations.groq_client.requests.post')
    def test_http_error_returns_fallback(self, mock_post):
        """Test HTTP error returns fallback response (Requirement 15.3)"""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError()
        mock_post.return_value = mock_response
        
        client = GroqClient(api_key='test-key')
        
        # Act
        result = client.generate_response('test')
        
        # Assert
        assert 'unable to process your request' in result.lower()
    
    @patch('backend.integrations.groq_client.requests.post')
    def test_request_exception_returns_fallback(self, mock_post):
        """Test request exception returns fallback response (Requirement 15.3)"""
        # Arrange
        mock_post.side_effect = requests.exceptions.RequestException()
        client = GroqClient(api_key='test-key')
        
        # Act
        result = client.generate_response('test')
        
        # Assert
        assert 'unable to process your request' in result.lower()
    
    @patch('backend.integrations.groq_client.requests.post')
    def test_malformed_response_returns_fallback(self, mock_post):
        """Test malformed response returns fallback (Requirement 15.3)"""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'invalid': 'structure'
        }
        mock_post.return_value = mock_response
        
        client = GroqClient(api_key='test-key')
        
        # Act
        result = client.generate_response('test')
        
        # Assert
        assert 'unable to process your request' in result.lower()
    
    @patch('backend.integrations.groq_client.requests.post')
    def test_missing_choices_returns_fallback(self, mock_post):
        """Test missing choices in response returns fallback"""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {}
        mock_post.return_value = mock_response
        
        client = GroqClient(api_key='test-key')
        
        # Act
        result = client.generate_response('test')
        
        # Assert
        assert 'unable to process your request' in result.lower()
    
    @patch('backend.integrations.groq_client.requests.post')
    def test_unexpected_exception_returns_fallback(self, mock_post):
        """Test unexpected exception returns fallback (Requirement 15.3)"""
        # Arrange
        mock_post.side_effect = Exception('Unexpected error')
        client = GroqClient(api_key='test-key')
        
        # Act
        result = client.generate_response('test')
        
        # Assert
        assert 'unable to process your request' in result.lower()


class TestGroqClientMetricsLogging:
    """Test metrics logging (Requirement 14.2)"""
    
    @patch('backend.integrations.groq_client.requests.post')
    @patch('backend.integrations.groq_client.logger')
    def test_logs_response_time_and_tokens(self, mock_logger, mock_post):
        """Test that response time and token usage are logged (Requirement 14.2)"""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'choices': [{'message': {'content': 'response'}}],
            'usage': {
                'prompt_tokens': 100,
                'completion_tokens': 50,
                'total_tokens': 150
            }
        }
        mock_post.return_value = mock_response
        
        client = GroqClient(api_key='test-key')
        
        # Act
        client.generate_response('test')
        
        # Assert
        # Check that info log was called with metrics
        info_calls = [call for call in mock_logger.info.call_args_list]
        assert len(info_calls) > 0
        
        # Verify metrics are in log message
        log_message = str(info_calls[0])
        assert 'response_time' in log_message
        assert 'prompt_tokens=100' in log_message
        assert 'completion_tokens=50' in log_message
        assert 'total_tokens=150' in log_message
    
    @patch('backend.integrations.groq_client.requests.post')
    @patch('backend.integrations.groq_client.logger')
    def test_logs_with_missing_usage_data(self, mock_logger, mock_post):
        """Test logging handles missing usage data gracefully"""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'choices': [{'message': {'content': 'response'}}],
            'usage': {}  # Empty usage
        }
        mock_post.return_value = mock_response
        
        client = GroqClient(api_key='test-key')
        
        # Act
        client.generate_response('test')
        
        # Assert - should not raise exception
        info_calls = [call for call in mock_logger.info.call_args_list]
        assert len(info_calls) > 0
        log_message = str(info_calls[0])
        assert 'prompt_tokens=0' in log_message
        assert 'completion_tokens=0' in log_message
    
    @patch('backend.integrations.groq_client.requests.post')
    @patch('backend.integrations.groq_client.logger')
    def test_logs_errors_on_failure(self, mock_logger, mock_post):
        """Test that errors are logged on API failure"""
        # Arrange
        mock_post.side_effect = requests.exceptions.Timeout()
        client = GroqClient(api_key='test-key')
        
        # Act
        client.generate_response('test')
        
        # Assert
        mock_logger.error.assert_called()
        error_message = str(mock_logger.error.call_args)
        assert 'timeout' in error_message.lower()


class TestGroqClientAvailability:
    """Test availability health check"""
    
    @patch('backend.integrations.groq_client.requests.post')
    def test_is_available_returns_true_on_success(self, mock_post):
        """Test is_available returns True when API responds"""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        client = GroqClient(api_key='test-key')
        
        # Act
        result = client.is_available()
        
        # Assert
        assert result is True
    
    @patch('backend.integrations.groq_client.requests.post')
    def test_is_available_returns_false_on_error(self, mock_post):
        """Test is_available returns False on error"""
        # Arrange
        mock_post.side_effect = requests.exceptions.RequestException()
        client = GroqClient(api_key='test-key')
        
        # Act
        result = client.is_available()
        
        # Assert
        assert result is False
    
    @patch('backend.integrations.groq_client.requests.post')
    def test_is_available_returns_false_on_non_200(self, mock_post):
        """Test is_available returns False on non-200 status"""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 500
        mock_post.return_value = mock_response
        
        client = GroqClient(api_key='test-key')
        
        # Act
        result = client.is_available()
        
        # Assert
        assert result is False
    
    @patch('backend.integrations.groq_client.requests.post')
    def test_is_available_uses_minimal_request(self, mock_post):
        """Test is_available uses minimal test request"""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        client = GroqClient(api_key='test-key')
        
        # Act
        client.is_available()
        
        # Assert
        call_args = mock_post.call_args
        assert call_args[1]['json']['messages'][0]['content'] == 'test'
        assert call_args[1]['json']['max_tokens'] == 5
        assert call_args[1]['timeout'] == 5


class TestGroqClientFallbackResponse:
    """Test fallback response content"""
    
    def test_fallback_response_content(self):
        """Test fallback response contains required information"""
        client = GroqClient(api_key='test-key')
        fallback = client._get_fallback_response()
        
        # Should mention technical issue
        assert 'technical issue' in fallback.lower() or 'unable to process' in fallback.lower()
        
        # Should advise seeking medical care
        assert 'medical care' in fallback.lower() or 'doctor' in fallback.lower()
        
        # Should mention emergency services
        assert '911' in fallback or 'emergency' in fallback.lower()
    
    def test_fallback_response_is_string(self):
        """Test fallback response is a string"""
        client = GroqClient(api_key='test-key')
        fallback = client._get_fallback_response()
        
        assert isinstance(fallback, str)
        assert len(fallback) > 0


class TestGroqClientEdgeCases:
    """Test edge cases and boundary conditions"""
    
    @patch('backend.integrations.groq_client.requests.post')
    def test_empty_prompt(self, mock_post):
        """Test handling of empty prompt"""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'choices': [{'message': {'content': 'response'}}],
            'usage': {}
        }
        mock_post.return_value = mock_response
        
        client = GroqClient(api_key='test-key')
        
        # Act
        result = client.generate_response('')
        
        # Assert - should still make request
        mock_post.assert_called_once()
    
    @patch('backend.integrations.groq_client.requests.post')
    def test_very_long_prompt(self, mock_post):
        """Test handling of very long prompt"""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'choices': [{'message': {'content': 'response'}}],
            'usage': {}
        }
        mock_post.return_value = mock_response
        
        client = GroqClient(api_key='test-key')
        long_prompt = 'test ' * 10000
        
        # Act
        result = client.generate_response(long_prompt)
        
        # Assert - should handle without error
        assert result == 'response'
    
    @patch('backend.integrations.groq_client.requests.post')
    def test_special_characters_in_prompt(self, mock_post):
        """Test handling of special characters in prompt"""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'choices': [{'message': {'content': 'response'}}],
            'usage': {}
        }
        mock_post.return_value = mock_response
        
        client = GroqClient(api_key='test-key')
        special_prompt = 'Test with "quotes" and \'apostrophes\' and \n newlines'
        
        # Act
        result = client.generate_response(special_prompt)
        
        # Assert
        assert result == 'response'
        call_args = mock_post.call_args
        assert call_args[1]['json']['messages'][0]['content'] == special_prompt
    
    @patch('backend.integrations.groq_client.requests.post')
    def test_zero_temperature(self, mock_post):
        """Test temperature of 0 (deterministic)"""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'choices': [{'message': {'content': 'response'}}],
            'usage': {}
        }
        mock_post.return_value = mock_response
        
        client = GroqClient(api_key='test-key')
        
        # Act
        client.generate_response('test', temperature=0.0)
        
        # Assert
        call_args = mock_post.call_args
        assert call_args[1]['json']['temperature'] == 0.0
    
    @patch('backend.integrations.groq_client.requests.post')
    def test_max_temperature(self, mock_post):
        """Test maximum temperature (creative)"""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'choices': [{'message': {'content': 'response'}}],
            'usage': {}
        }
        mock_post.return_value = mock_response
        
        client = GroqClient(api_key='test-key')
        
        # Act
        client.generate_response('test', temperature=2.0)
        
        # Assert
        call_args = mock_post.call_args
        assert call_args[1]['json']['temperature'] == 2.0
