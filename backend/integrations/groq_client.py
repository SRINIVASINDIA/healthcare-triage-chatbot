"""
Groq API Client for LLM integration
Validates Requirements 14.2, 15.3
"""

import requests
import logging
import time
from typing import Optional

logger = logging.getLogger(__name__)


class GroqClient:
    """
    Wrapper for Groq API to generate AI responses.
    
    Validates Requirements:
    - 14.2: Log AI model response times and token usage
    - 15.3: Provide fallback response when service unavailable
    """
    
    GROQ_API_URL = 'https://api.groq.com/openai/v1/chat/completions'
    DEFAULT_TEMPERATURE = 0.3
    DEFAULT_MAX_TOKENS = 500
    DEFAULT_TIMEOUT = 10  # seconds
    
    def __init__(self, api_key: str, model: str = 'llama-3.1-8b-instant'):
        """
        Initialize Groq API client.
        
        Args:
            api_key: Groq API key for authentication
            model: Model name to use (default: llama-3.1-8b-instant)
        """
        self.api_key = api_key
        self.model = model
    
    def generate_response(self, prompt: str, temperature: float = None, max_tokens: int = None) -> str:
        """
        Generate AI response from prompt with error handling.
        
        Args:
            prompt: The prompt to send to the AI model
            temperature: Sampling temperature (default: 0.3)
            max_tokens: Maximum tokens in response (default: 500)
        
        Returns:
            AI-generated response string, or fallback response if service unavailable
        
        Validates: Requirements 14.2, 15.3
        """
        if temperature is None:
            temperature = self.DEFAULT_TEMPERATURE
        if max_tokens is None:
            max_tokens = self.DEFAULT_MAX_TOKENS
        
        start_time = time.time()
        
        try:
            # Prepare request
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            
            payload = {
                'model': self.model,
                'messages': [
                    {'role': 'user', 'content': prompt}
                ],
                'temperature': temperature,
                'max_tokens': max_tokens
            }
            
            # Make API request
            response = requests.post(
                self.GROQ_API_URL,
                headers=headers,
                json=payload,
                timeout=self.DEFAULT_TIMEOUT
            )
            
            # Calculate response time
            response_time = time.time() - start_time
            
            # Check for errors
            response.raise_for_status()
            
            # Parse response
            result = response.json()
            content = result['choices'][0]['message']['content']
            
            # Log metrics
            usage = result.get('usage', {})
            self._log_metrics(response_time, usage)
            
            return content
        
        except requests.exceptions.Timeout:
            logger.error(f"Groq API timeout after {self.DEFAULT_TIMEOUT} seconds")
            return self._get_fallback_response()
        
        except requests.exceptions.HTTPError as e:
            logger.error(f"Groq API HTTP error: {e}")
            return self._get_fallback_response()
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Groq API request error: {e}")
            return self._get_fallback_response()
        
        except (KeyError, IndexError) as e:
            logger.error(f"Groq API response parsing error: {e}")
            return self._get_fallback_response()
        
        except Exception as e:
            logger.error(f"Unexpected error calling Groq API: {e}")
            return self._get_fallback_response()
    
    def is_available(self) -> bool:
        """
        Health check for Groq API availability.
        
        Returns:
            True if API is available, False otherwise
        """
        try:
            # Make a minimal test request
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            
            payload = {
                'model': self.model,
                'messages': [
                    {'role': 'user', 'content': 'test'}
                ],
                'max_tokens': 5
            }
            
            response = requests.post(
                self.GROQ_API_URL,
                headers=headers,
                json=payload,
                timeout=5
            )
            
            return response.status_code == 200
        
        except Exception as e:
            logger.warning(f"Groq API health check failed: {e}")
            return False
    
    def _log_metrics(self, response_time: float, usage: dict) -> None:
        """
        Log AI model response times and token usage.
        
        Args:
            response_time: Time taken for API response in seconds
            usage: Token usage dictionary from API response
        
        Validates: Requirement 14.2
        """
        prompt_tokens = usage.get('prompt_tokens', 0)
        completion_tokens = usage.get('completion_tokens', 0)
        total_tokens = usage.get('total_tokens', 0)
        
        logger.info(
            f"Groq API metrics: response_time={response_time:.2f}s, "
            f"prompt_tokens={prompt_tokens}, "
            f"completion_tokens={completion_tokens}, "
            f"total_tokens={total_tokens}"
        )
    
    def _get_fallback_response(self) -> str:
        """
        Return fallback response when AI service is unavailable.
        
        Returns:
            Fallback response advising in-person medical care
        
        Validates: Requirement 15.3
        """
        return (
            "I'm unable to process your request at this time due to a technical issue. "
            "For your safety, please seek in-person medical care or call your doctor "
            "for proper evaluation of your symptoms. If you're experiencing a medical "
            "emergency, please call 911 or go to the nearest emergency room immediately."
        )
