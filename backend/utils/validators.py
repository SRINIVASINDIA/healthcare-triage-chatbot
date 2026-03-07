"""
Input validators and sanitizers for security
"""

import re
import html
from typing import Tuple, Optional
from .exceptions import ValidationException


def validate_message_request(request: dict) -> Tuple[bool, Optional[str]]:
    """Validate WebSocket message request"""
    # Check for required fields
    if 'action' not in request:
        return False, "Missing 'action' field"
    
    if request['action'] != 'sendMessage':
        return False, f"Invalid action: {request['action']}"
    
    if 'sessionId' not in request:
        return False, "Missing 'sessionId' field"
    
    if 'message' not in request:
        return False, "Missing 'message' field"
    
    # Validate session ID format
    is_valid, error = validate_session_id(request['sessionId'])
    if not is_valid:
        return False, error
    
    # Validate message content
    message = request['message']
    if not isinstance(message, str):
        return False, "Message must be a string"
    
    message = message.strip()
    if not message:
        return False, "Message cannot be empty"
    
    if len(message) > 2000:
        return False, "Message exceeds 2000 character limit"
    
    return True, None


def sanitize_message(message: str) -> str:
    """Sanitize message to prevent injection attacks"""
    if not isinstance(message, str):
        raise ValidationException("Message must be a string")
    
    # HTML escape to prevent XSS
    message = html.escape(message)
    
    # Remove control characters except newlines and tabs
    message = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', message)
    
    # Limit consecutive whitespace
    message = re.sub(r'\s+', ' ', message)
    
    return message.strip()


def validate_session_id(session_id: str) -> Tuple[bool, Optional[str]]:
    """Validate session ID format (UUID v4)"""
    if not isinstance(session_id, str):
        return False, "Session ID must be a string"
    
    # UUID v4 pattern
    uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'
    
    if not re.match(uuid_pattern, session_id, re.IGNORECASE):
        return False, "Invalid session ID format (must be UUID v4)"
    
    return True, None


# Rate limiting state (in-memory for simplicity)
_rate_limit_state = {}


def check_rate_limit(session_id: str, max_per_minute: int = 10, max_per_hour: int = 100) -> Tuple[bool, Optional[str]]:
    """Check rate limits for a session"""
    import time
    
    current_time = time.time()
    
    if session_id not in _rate_limit_state:
        _rate_limit_state[session_id] = {
            'minute_count': 0,
            'minute_reset': current_time + 60,
            'hour_count': 0,
            'hour_reset': current_time + 3600
        }
    
    state = _rate_limit_state[session_id]
    
    # Reset counters if time windows expired
    if current_time > state['minute_reset']:
        state['minute_count'] = 0
        state['minute_reset'] = current_time + 60
    
    if current_time > state['hour_reset']:
        state['hour_count'] = 0
        state['hour_reset'] = current_time + 3600
    
    # Check limits
    if state['minute_count'] >= max_per_minute:
        return False, "Rate limit exceeded: too many messages per minute"
    
    if state['hour_count'] >= max_per_hour:
        return False, "Rate limit exceeded: too many messages per hour"
    
    # Increment counters
    state['minute_count'] += 1
    state['hour_count'] += 1
    
    return True, None
