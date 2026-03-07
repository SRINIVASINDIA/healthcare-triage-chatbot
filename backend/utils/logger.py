"""
Logging configuration with structured JSON format and PII redaction
"""

import logging
import json
import re
from typing import Any, Dict


def configure_logger(name: str) -> logging.Logger:
    """Configure structured logger with JSON format"""
    logger = logging.getLogger(name)
    
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    
    return logger


class JsonFormatter(logging.Formatter):
    """Format logs as JSON for CloudWatch"""
    
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            'timestamp': self.formatTime(record),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
        }
        
        # Add extra fields if present
        if hasattr(record, 'extra'):
            log_data.update(record.extra)
        
        # Redact sensitive data
        log_data = redact_sensitive_data(log_data)
        
        return json.dumps(log_data)


def redact_sensitive_data(data: Any) -> Any:
    """Redact PII from log data"""
    if isinstance(data, dict):
        redacted = {}
        for key, value in data.items():
            # Redact sensitive keys
            if key.lower() in ['password', 'api_key', 'token', 'secret', 'authorization']:
                redacted[key] = '***REDACTED***'
            else:
                redacted[key] = redact_sensitive_data(value)
        return redacted
    
    elif isinstance(data, list):
        return [redact_sensitive_data(item) for item in data]
    
    elif isinstance(data, str):
        # Redact email addresses
        data = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL]', data)
        # Redact phone numbers (basic pattern)
        data = re.sub(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', '[PHONE]', data)
        # Redact SSN-like patterns
        data = re.sub(r'\b\d{3}-\d{2}-\d{4}\b', '[SSN]', data)
        return data
    
    return data


def log_audit_event(event_type: str, details: Dict[str, Any], logger: logging.Logger = None):
    """Log security and audit events"""
    if logger is None:
        logger = configure_logger('audit')
    
    audit_data = {
        'event_type': event_type,
        'details': details,
        'audit': True
    }
    
    logger.info(f"Audit event: {event_type}", extra=audit_data)
