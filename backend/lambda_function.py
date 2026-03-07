"""
Healthcare Triage Chatbot - Lambda Function
Provides AI-powered symptom triage using Groq API
Supports both REST API (backward compatible) and WebSocket modes
"""

import json
import os
import urllib.request
import urllib.error
from typing import Dict, Any, Optional
import logging
from datetime import datetime, timezone

# Import session management modules for temporary session support
try:
    from core.models import ConversationSession, Message, MessageRole, ConversationState
    from core.emergency_detector import EmergencyDetector
    SESSION_SUPPORT_ENABLED = True
except ImportError:
    SESSION_SUPPORT_ENABLED = False
    logging.warning("Session management modules not available, using legacy mode")

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Emergency keywords that trigger immediate SEVERE classification (legacy fallback)
EMERGENCY_KEYWORDS = [
    "chest pain",
    "stroke",
    "seizure",
    "severe bleeding",
    "difficulty breathing",
    "unconscious",
    "suicide"
]

# Groq API configuration
GROQ_API_KEY = os.environ.get('GROQ_API_KEY', '')
GROQ_MODEL = os.environ.get('GROQ_MODEL', 'llama-3.1-8b-instant')
GROQ_API_URL = 'https://api.groq.com/openai/v1/chat/completions'
TEMPERATURE = 0.3
MAX_TOKENS = 500

# Initialize emergency detector if available
emergency_detector = EmergencyDetector() if SESSION_SUPPORT_ENABLED else None


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main Lambda handler for triage requests
    Supports both REST API (backward compatible) and temporary session mode
    
    Args:
        event: API Gateway event object
        context: Lambda context object
        
    Returns:
        API Gateway response with triage result
    """
    request_id = context.aws_request_id if context else 'unknown'
    
    try:
        # Parse request body
        body = json.loads(event.get('body', '{}'))
        symptoms = body.get('symptoms', '').strip()
        
        # Validate input
        if not symptoms:
            logger.warning(f"Request {request_id}: Missing symptoms field")
            return create_error_response(400, 'Invalid request: symptoms field is required')
        
        if len(symptoms) > 2000:
            logger.warning(f"Request {request_id}: Symptoms exceed 2000 characters")
            return create_error_response(400, 'Invalid request: symptoms field must not exceed 2000 characters')
        
        # Log REST API usage for analytics (Requirement 12.7)
        logger.info(f"Request {request_id}: REST API request received", extra={
            "api_type": "REST",
            "message_length": len(symptoms),
            "request_id": request_id
        })
        
        # Create temporary single-turn session if session support enabled (Requirement 12.2)
        temp_session = None
        if SESSION_SUPPORT_ENABLED:
            temp_session = create_temporary_session(symptoms)
        
        # Check for emergency keywords using session-based or legacy detection
        is_emergency = False
        if temp_session and emergency_detector:
            # Use session-based emergency detection (Requirement 12.4)
            is_emergency = emergency_detector.detect_emergency(temp_session.message_history)
        else:
            # Fallback to legacy detection
            is_emergency = detect_emergency(symptoms)
        
        if is_emergency:
            logger.info(f"Request {request_id}: Emergency keywords detected")
            triage_response = create_emergency_response()
        else:
            # Invoke Groq for non-emergency symptoms
            logger.info(f"Request {request_id}: Invoking Groq for non-emergency symptoms")
            triage_response = invoke_groq(symptoms, request_id)
        
        # Return successful response in original format (Requirement 12.3)
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type',
                'Access-Control-Allow-Methods': 'POST, OPTIONS'
            },
            'body': json.dumps({
                'severity': triage_response['severity'],
                'advice': sanitize_response_data(triage_response['advice'])
            })
        }
    
    except json.JSONDecodeError as e:
        logger.error(f"Request {request_id}: JSON decode error - {str(e)}")
        return create_error_response(400, 'Invalid request: malformed JSON in request body')
        
    except Exception as e:
        logger.error(f"Request {request_id}: Unexpected error - {str(e)}")
        # Return fallback triage response for unexpected errors
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'severity': 'MODERATE',
                'advice': 'Internal server error. Please seek in-person medical care.'
            })
        }


def create_temporary_session(symptoms: str) -> Optional[ConversationSession]:
    """
    Create a temporary single-turn session for REST API requests
    Session is not persisted to DynamoDB (Requirement 12.2, 12.5)
    
    Args:
        symptoms: User's symptom description
        
    Returns:
        Temporary ConversationSession object (in-memory only)
    """
    try:
        now = datetime.now(timezone.utc).isoformat()
        
        # Create user message
        user_message = Message(
            timestamp=now,
            role=MessageRole.USER,
            content=symptoms,
            extracted_entities=[]
        )
        
        # Create temporary session (not stored in DynamoDB)
        session = ConversationSession(
            session_id="temp-rest-api",  # Temporary ID
            created_at=now,
            last_updated_at=now,
            ttl=0,  # No TTL for temporary session
            conversation_state=ConversationState.INITIAL,
            message_history=[user_message],
            aggregated_entities={},
            follow_up_count=0,
            emergency_detected=False
        )
        
        return session
    
    except Exception as e:
        logger.error(f"Error creating temporary session: {str(e)}")
        return None


def detect_emergency(symptoms: str) -> bool:
    """
    Check if symptoms contain emergency keywords
    
    Args:
        symptoms: User's symptom description
        
    Returns:
        True if emergency keywords detected, False otherwise
    """
    symptoms_lower = symptoms.lower()
    return any(keyword in symptoms_lower for keyword in EMERGENCY_KEYWORDS)


def create_emergency_response() -> Dict[str, str]:
    """
    Create immediate emergency response
    
    Returns:
        Triage response with SEVERE severity and emergency advice
    """
    return {
        'severity': 'SEVERE',
        'advice': 'Call 911 or go to the nearest emergency room immediately. Your symptoms may indicate a medical emergency that requires immediate professional attention.'
    }


def invoke_groq(symptoms: str, request_id: str = 'unknown') -> Dict[str, str]:
    """
    Invoke Groq API for symptom analysis
    
    Args:
        symptoms: User's symptom description
        request_id: Request ID for logging
        
    Returns:
        Triage response with severity and advice
    """
    try:
        if not GROQ_API_KEY:
            logger.error(f"Request {request_id}: Groq API key not configured")
            return create_fallback_response()
        
        # Format prompt for Groq
        prompt = format_groq_prompt(symptoms)
        
        # Prepare request body (OpenAI-compatible format)
        request_body = {
            "model": GROQ_MODEL,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a medical triage assistant. Analyze symptoms and provide severity classification and advice."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": TEMPERATURE,
            "max_tokens": MAX_TOKENS
        }
        
        # Make HTTP request to Groq API
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {GROQ_API_KEY}',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        data = json.dumps(request_body).encode('utf-8')
        
        req = urllib.request.Request(GROQ_API_URL, data=data, headers=headers, method='POST')
        
        with urllib.request.urlopen(req, timeout=10) as response:
            result = json.loads(response.read().decode('utf-8'))
        
        logger.info(f"Request {request_id}: Successfully received Groq response")
        return parse_groq_response(result)
    
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8') if e.fp else str(e)
        logger.error(f"Request {request_id}: Groq HTTP error {e.code} - {error_body}")
        logger.error(f"Request {request_id}: Full error details: {str(e)}")
        return create_fallback_response()
    
    except urllib.error.URLError as e:
        logger.error(f"Request {request_id}: Groq URL error - {str(e)}")
        logger.error(f"Request {request_id}: Error reason: {e.reason if hasattr(e, 'reason') else 'unknown'}")
        return create_fallback_response()
    
    except Exception as e:
        logger.error(f"Request {request_id}: Groq invocation error - {type(e).__name__} - {str(e)}")
        import traceback
        logger.error(f"Request {request_id}: Traceback: {traceback.format_exc()}")
        return create_fallback_response()


def format_groq_prompt(symptoms: str) -> str:
    """
    Format prompt for Groq
    
    Args:
        symptoms: User's symptom description
        
    Returns:
        Formatted prompt string
    """
    return f"""Analyze the following symptoms and provide:
1. A severity classification: LOW, MODERATE, or SEVERE
2. Appropriate medical advice

Symptoms: {symptoms}

Respond in this exact format:
SEVERITY: [LOW/MODERATE/SEVERE]
ADVICE: [Your medical guidance]

Guidelines:
- LOW: Minor symptoms that can be managed at home or with over-the-counter remedies
- MODERATE: Symptoms that warrant seeing a doctor within 24-48 hours
- SEVERE: Symptoms requiring urgent medical attention within hours

Provide clear, actionable advice appropriate for the severity level."""


def parse_groq_response(response: Dict[str, Any]) -> Dict[str, str]:
    """
    Parse Groq API response
    
    Args:
        response: Groq API response object
        
    Returns:
        Triage response with severity and advice
    """
    try:
        # Extract content from response (OpenAI-compatible format)
        choices = response.get('choices', [])
        if not choices:
            raise ValueError("No choices in response")
        
        message = choices[0].get('message', {})
        text = message.get('content', '')
        
        # Parse severity and advice
        severity = 'MODERATE'  # Default
        advice = ''
        
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith('SEVERITY:'):
                severity_value = line.replace('SEVERITY:', '').strip().upper()
                if severity_value in ['LOW', 'MODERATE', 'SEVERE']:
                    severity = severity_value
            elif line.startswith('ADVICE:'):
                advice = line.replace('ADVICE:', '').strip()
        
        # If advice not found in expected format, use fallback advice
        if not advice:
            advice = 'Please consult with a healthcare provider about your symptoms.'
        
        return {
            'severity': severity,
            'advice': advice
        }
        
    except Exception as e:
        logger.error(f"Error parsing Groq response: {str(e)}")
        return {
            'severity': 'MODERATE',
            'advice': 'Please consult with a healthcare provider about your symptoms.'
        }


def invoke_deepseek(symptoms: str, request_id: str = 'unknown') -> Dict[str, str]:
    """
    Invoke DeepSeek API for symptom analysis
    
    Args:
        symptoms: User's symptom description
        request_id: Request ID for logging
        
    Returns:
        Triage response with severity and advice
    """
    try:
        if not DEEPSEEK_API_KEY:
            logger.error(f"Request {request_id}: DeepSeek API key not configured")
            return create_fallback_response()
        
        # Format prompt for DeepSeek
        prompt = format_deepseek_prompt(symptoms)
        
        # Prepare request body (OpenAI-compatible format)
        request_body = {
            "model": DEEPSEEK_MODEL,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a medical triage assistant. Analyze symptoms and provide severity classification and advice."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": TEMPERATURE,
            "max_tokens": MAX_TOKENS
        }
        
        # Make HTTP request to DeepSeek API
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {DEEPSEEK_API_KEY}'
        }
        data = json.dumps(request_body).encode('utf-8')
        
        req = urllib.request.Request(DEEPSEEK_API_URL, data=data, headers=headers, method='POST')
        
        with urllib.request.urlopen(req, timeout=10) as response:
            result = json.loads(response.read().decode('utf-8'))
        
        logger.info(f"Request {request_id}: Successfully received DeepSeek response")
        return parse_deepseek_response(result)
    
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8') if e.fp else str(e)
        logger.error(f"Request {request_id}: DeepSeek HTTP error {e.code} - {error_body}")
        return create_fallback_response()
    
    except urllib.error.URLError as e:
        logger.error(f"Request {request_id}: DeepSeek URL error - {str(e)}")
        return create_fallback_response()
    
    except Exception as e:
        logger.error(f"Request {request_id}: DeepSeek invocation error - {type(e).__name__} - {str(e)}")
        return create_fallback_response()


def format_deepseek_prompt(symptoms: str) -> str:
    """
    Format prompt for DeepSeek
    
    Args:
        symptoms: User's symptom description
        
    Returns:
        Formatted prompt string
    """
    return f"""Analyze the following symptoms and provide:
1. A severity classification: LOW, MODERATE, or SEVERE
2. Appropriate medical advice

Symptoms: {symptoms}

Respond in this exact format:
SEVERITY: [LOW/MODERATE/SEVERE]
ADVICE: [Your medical guidance]

Guidelines:
- LOW: Minor symptoms that can be managed at home or with over-the-counter remedies
- MODERATE: Symptoms that warrant seeing a doctor within 24-48 hours
- SEVERE: Symptoms requiring urgent medical attention within hours

Provide clear, actionable advice appropriate for the severity level."""


def parse_deepseek_response(response: Dict[str, Any]) -> Dict[str, str]:
    """
    Parse DeepSeek API response
    
    Args:
        response: DeepSeek API response object
        
    Returns:
        Triage response with severity and advice
    """
    try:
        # Extract content from response (OpenAI-compatible format)
        choices = response.get('choices', [])
        if not choices:
            raise ValueError("No choices in response")
        
        message = choices[0].get('message', {})
        text = message.get('content', '')
        
        # Parse severity and advice
        severity = 'MODERATE'  # Default
        advice = ''
        
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith('SEVERITY:'):
                severity_value = line.replace('SEVERITY:', '').strip().upper()
                if severity_value in ['LOW', 'MODERATE', 'SEVERE']:
                    severity = severity_value
            elif line.startswith('ADVICE:'):
                advice = line.replace('ADVICE:', '').strip()
        
        # If advice not found in expected format, use fallback advice
        if not advice:
            advice = 'Please consult with a healthcare provider about your symptoms.'
        
        return {
            'severity': severity,
            'advice': advice
        }
        
    except Exception as e:
        logger.error(f"Error parsing DeepSeek response: {str(e)}")
        return {
            'severity': 'MODERATE',
            'advice': 'Please consult with a healthcare provider about your symptoms.'
        }


def invoke_gemini(symptoms: str, request_id: str = 'unknown') -> Dict[str, str]:
    """
    Invoke Google Gemini API for symptom analysis
    
    Args:
        symptoms: User's symptom description
        request_id: Request ID for logging
        
    Returns:
        Triage response with severity and advice
    """
    try:
        if not GEMINI_API_KEY:
            logger.error(f"Request {request_id}: Gemini API key not configured")
            return create_fallback_response()
        
        # Format prompt for Gemini
        prompt = format_gemini_prompt(symptoms)
        
        # Prepare request body
        request_body = {
            "contents": [{
                "parts": [{
                    "text": prompt
                }]
            }],
            "generationConfig": {
                "temperature": TEMPERATURE,
                "maxOutputTokens": MAX_TOKENS,
                "topP": 0.9,
                "topK": 40
            }
        }
        
        # Make HTTP request to Gemini API
        url = GEMINI_API_URL
        headers = {'Content-Type': 'application/json'}
        data = json.dumps(request_body).encode('utf-8')
        
        req = urllib.request.Request(url, data=data, headers=headers, method='POST')
        
        with urllib.request.urlopen(req, timeout=10) as response:
            result = json.loads(response.read().decode('utf-8'))
        
        logger.info(f"Request {request_id}: Successfully received Gemini response")
        return parse_gemini_response(result)
    
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8') if e.fp else str(e)
        logger.error(f"Request {request_id}: Gemini HTTP error {e.code} - {error_body}")
        return create_fallback_response()
    
    except urllib.error.URLError as e:
        logger.error(f"Request {request_id}: Gemini URL error - {str(e)}")
        return create_fallback_response()
    
    except Exception as e:
        logger.error(f"Request {request_id}: Gemini invocation error - {type(e).__name__} - {str(e)}")
        return create_fallback_response()


def format_gemini_prompt(symptoms: str) -> str:
    """
    Format prompt for Google Gemini
    
    Args:
        symptoms: User's symptom description
        
    Returns:
        Formatted prompt string
    """
    return f"""You are a medical triage assistant. Analyze the following symptoms and provide:
1. A severity classification: LOW, MODERATE, or SEVERE
2. Appropriate medical advice

Symptoms: {symptoms}

Respond in this exact format:
SEVERITY: [LOW/MODERATE/SEVERE]
ADVICE: [Your medical guidance]

Guidelines:
- LOW: Minor symptoms that can be managed at home or with over-the-counter remedies
- MODERATE: Symptoms that warrant seeing a doctor within 24-48 hours
- SEVERE: Symptoms requiring urgent medical attention within hours

Provide clear, actionable advice appropriate for the severity level."""


def parse_gemini_response(response: Dict[str, Any]) -> Dict[str, str]:
    """
    Parse Gemini API response
    
    Args:
        response: Gemini API response object
        
    Returns:
        Triage response with severity and advice
    """
    try:
        # Extract content from response
        candidates = response.get('candidates', [])
        if not candidates:
            raise ValueError("No candidates in response")
        
        content = candidates[0].get('content', {})
        parts = content.get('parts', [])
        if not parts:
            raise ValueError("No parts in response")
        
        text = parts[0].get('text', '')
        
        # Parse severity and advice
        severity = 'MODERATE'  # Default
        advice = ''
        
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith('SEVERITY:'):
                severity_value = line.replace('SEVERITY:', '').strip().upper()
                if severity_value in ['LOW', 'MODERATE', 'SEVERE']:
                    severity = severity_value
            elif line.startswith('ADVICE:'):
                advice = line.replace('ADVICE:', '').strip()
        
        # If advice not found in expected format, use fallback advice
        if not advice:
            advice = 'Please consult with a healthcare provider about your symptoms.'
        
        return {
            'severity': severity,
            'advice': advice
        }
        
    except Exception as e:
        logger.error(f"Error parsing Gemini response: {str(e)}")
        return {
            'severity': 'MODERATE',
            'advice': 'Please consult with a healthcare provider about your symptoms.'
        }


def invoke_bedrock(symptoms: str, request_id: str = 'unknown') -> Dict[str, str]:
    """
    Invoke SageMaker endpoint for symptom analysis
    
    Args:
        symptoms: User's symptom description
        request_id: Request ID for logging
        
    Returns:
        Triage response with severity and advice
    """
    try:
        if not SAGEMAKER_ENDPOINT:
            logger.error(f"Request {request_id}: SageMaker endpoint not configured")
            return create_fallback_response()
        
        # Format prompt for the model
        prompt = format_prompt_for_model(symptoms)
        
        # Prepare request payload (adjust based on your model's expected format)
        # This example is for Llama 2 / Mistral format
        payload = {
            "inputs": prompt,
            "parameters": {
                "temperature": TEMPERATURE,
                "max_new_tokens": MAX_TOKENS,
                "top_p": 0.9,
                "do_sample": True
            }
        }
        
        # Invoke SageMaker endpoint
        response = sagemaker_runtime.invoke_endpoint(
            EndpointName=SAGEMAKER_ENDPOINT,
            ContentType='application/json',
            Body=json.dumps(payload)
        )
        
        # Parse response
        result = json.loads(response['Body'].read().decode())
        logger.info(f"Request {request_id}: Successfully received SageMaker response")
        
        return parse_model_response(result)
    
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        error_message = e.response.get('Error', {}).get('Message', str(e))
        logger.error(f"Request {request_id}: SageMaker error - {error_code} - {error_message}")
        return create_fallback_response()
    
    except Exception as e:
        logger.error(f"Request {request_id}: SageMaker invocation error - {type(e).__name__} - {str(e)}")
        return create_fallback_response()


def create_fallback_response() -> Dict[str, str]:
    """
    Create fallback response when AI is unavailable
    
    Returns:
        Triage response with MODERATE severity and advice to seek in-person care
    """
    return {
        'severity': 'MODERATE',
        'advice': "We're unable to process your request at this time. Please seek in-person medical care or call your doctor for proper evaluation of your symptoms."
    }


def create_error_response(status_code: int, message: str) -> Dict[str, Any]:
    """
    Create error response
    
    Args:
        status_code: HTTP status code
        message: Error message
        
    Returns:
        API Gateway error response
    """
    # Sanitize message to ensure no sensitive data is exposed
    sanitized_message = sanitize_response_data(message)
    
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        },
        'body': json.dumps({'error': sanitized_message})
    }


def sanitize_response_data(data: str) -> str:
    """
    Sanitize response data to remove any sensitive information
    
    Args:
        data: Response data to sanitize
        
    Returns:
        Sanitized data with sensitive information removed
    """
    # List of sensitive patterns to check for (all lowercase for case-insensitive matching)
    sensitive_patterns = [
        'aws_access_key_id',
        'aws_secret_access_key',
        'aws_session_token',
        'akia',  # AWS access key prefix
        'secret',
        'password',
        'token',
        'key',
        'credential'
    ]
    
    # Convert to lowercase for case-insensitive checking
    data_lower = data.lower()
    
    # Check if any sensitive patterns are present
    for pattern in sensitive_patterns:
        if pattern in data_lower:
            logger.warning(f"Potential sensitive data detected in response: {pattern}")
            # Return generic error message if sensitive data detected
            return "An error occurred. Please try again or contact support."
    
    return data
