"""
Custom exception classes for error handling
"""


class SessionNotFoundException(Exception):
    """Raised when session is not found in DynamoDB"""
    pass


class ValidationException(Exception):
    """Raised when input validation fails"""
    pass


class ServiceUnavailableException(Exception):
    """Raised when external service is unavailable"""
    pass
