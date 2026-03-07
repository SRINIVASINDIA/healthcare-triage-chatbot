"""
WebSocket Connect Lambda Handler
Handles $connect route for WebSocket API
Validates Requirements 2.2, 2.3, 9.1, 9.2, 9.5, 14.3
"""

import json
import os
import logging
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.session_manager import SessionManager

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Environment variables
DYNAMODB_TABLE_NAME = os.environ.get('DYNAMODB_TABLE_NAME', 'healthcare-triage-conversations')
SESSION_TTL_HOURS = int(os.environ.get('SESSION_TTL_HOURS', '24'))


def lambda_handler(event, context):
    """
    Handle WebSocket connection initialization.
    
    Creates a new session or retrieves an existing one if sessionId provided.
    
    Args:
        event: API Gateway WebSocket event with query parameters
        context: Lambda context
        
    Returns:
        Response with statusCode 200 for success, 500 for errors
    
    Validates: Requirements 2.2, 2.3, 9.1, 9.2, 9.5, 14.3
    """
    import time
    start_time = time.time()
    
    connection_id = event['requestContext']['connectionId']
    
    try:
        # Extract sessionId from query parameters if provided
        query_params = event.get('queryStringParameters') or {}
        session_id = query_params.get('sessionId')
        
        # Log connection event (Requirement 14.3)
        logger.info(
            "WebSocket connection initiated",
            extra={
                "event_type": "connection",
                "connection_id": connection_id,
                "existing_session_id": session_id,
                "timestamp": time.time()
            }
        )
        
        # Initialize session manager
        session_manager = SessionManager(DYNAMODB_TABLE_NAME, SESSION_TTL_HOURS)
        
        # Try to retrieve existing session or create new one
        session_restored = False
        if session_id:
            logger.info(f"Attempting to retrieve existing session: {session_id}")
            session = session_manager.get_session(session_id)
            
            if session:
                logger.info(f"Retrieved existing session: {session_id}")
                session_restored = True
                # Update TTL for existing session
                session_manager.update_ttl(session_id)
            else:
                # Session not found or expired, create new one
                logger.info(f"Session {session_id} not found or expired, creating new session")
                session = session_manager.create_session()
        else:
            # No session ID provided, create new session
            logger.info("No session ID provided, creating new session")
            session = session_manager.create_session()
        
        # Calculate processing time
        processing_time = time.time() - start_time
        
        # Log successful connection with metrics (Requirement 14.3)
        logger.info(
            "WebSocket connected successfully",
            extra={
                "event_type": "connected",
                "connection_id": connection_id,
                "session_id": session.session_id,
                "session_restored": session_restored,
                "message_count": len(session.message_history),
                "processing_time_ms": int(processing_time * 1000)
            }
        )
        
        # Return success
        # Note: We can't send the session ID directly in the response body for $connect
        # The session ID will need to be sent in a separate message after connection
        # or stored in connection metadata
        return {
            'statusCode': 200
        }
    
    except Exception as e:
        logger.error(
            "Error handling WebSocket connection",
            extra={
                "event_type": "connection_error",
                "connection_id": connection_id,
                "error": str(e)
            },
            exc_info=True
        )
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'Internal server error'})
        }
