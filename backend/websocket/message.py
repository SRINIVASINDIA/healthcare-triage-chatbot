"""
WebSocket Message Lambda Handler
Handles sendMessage route for WebSocket API
Validates Requirements 2.4, 2.5, 3.1, 3.2, 3.3, 4.1, 4.3, 5.1, 6.1, 6.5, 15.1, 15.2, 15.3
"""

import json
import os
import logging
import sys
import boto3
from datetime import datetime, timezone

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.session_manager import SessionManager
from core.models import Message, MessageRole
from core.context_analyzer import ContextAnalyzer
from core.emergency_detector import EmergencyDetector
from core.followup_generator import FollowUpGenerator
from core.prompt_builder import PromptBuilder
from integrations.medical_ner import MedicalNERClient
from integrations.groq_client import GroqClient
from integrations.websocket_client import WebSocketClient

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Environment variables
DYNAMODB_TABLE_NAME = os.environ.get('DYNAMODB_TABLE_NAME', 'healthcare-triage-conversations')
GROQ_API_KEY = os.environ.get('GROQ_API_KEY', '')
GROQ_MODEL = os.environ.get('GROQ_MODEL', 'llama-3.1-8b-instant')
MAX_MESSAGES_PER_SESSION = int(os.environ.get('MAX_MESSAGES_PER_SESSION', '50'))
MAX_FOLLOW_UPS = int(os.environ.get('MAX_FOLLOW_UPS', '3'))


def lambda_handler(event, context):
    """
    Handle incoming WebSocket messages and generate responses.
    
    This is the main message processing pipeline that:
    1. Parses and validates the incoming message
    2. Retrieves the conversation session
    3. Extracts medical entities
    4. Checks for emergency keywords
    5. Analyzes conversation context
    6. Generates appropriate response (follow-up or triage)
    7. Updates the session
    8. Sends response back to client
    
    Args:
        event: API Gateway WebSocket event with message body
        context: Lambda context
        
    Returns:
        Response with statusCode 200 for success, 500 for errors
    
    Validates: Requirements 2.4, 2.5, 3.1, 3.2, 3.3, 4.1, 4.3, 5.1, 6.1, 6.5, 15.1, 15.2, 15.3
    """
    import time
    start_time = time.time()
    
    connection_id = event['requestContext']['connectionId']
    domain_name = event['requestContext']['domainName']
    stage = event['requestContext']['stage']
    
    # Initialize WebSocket client for sending responses
    api_gateway_management = boto3.client(
        'apigatewaymanagementapi',
        endpoint_url=f'https://{domain_name}/{stage}'
    )
    ws_client = WebSocketClient(api_gateway_management)
    
    # Metrics tracking
    metrics = {
        'message_length': 0,
        'entity_count': 0,
        'emergency_detected': False,
        'ai_response_time': 0,
        'total_processing_time': 0,
        'ner_processing_time': 0
    }
    
    try:
        # Parse request body
        body = json.loads(event.get('body', '{}'))
        action = body.get('action')
        session_id = body.get('sessionId')
        user_message = body.get('message', '').strip()
        
        metrics['message_length'] = len(user_message)
        
        # Validate request
        if action != 'sendMessage':
            ws_client.send_error(connection_id, f"Invalid action: {action}", "INVALID_ACTION")
            return {'statusCode': 400}
        
        if not session_id:
            ws_client.send_error(connection_id, "Missing sessionId", "MISSING_SESSION_ID")
            return {'statusCode': 400}
        
        if not user_message:
            ws_client.send_error(connection_id, "Message cannot be empty", "EMPTY_MESSAGE")
            return {'statusCode': 400}
        
        logger.info(f"Processing message: session_id={session_id}, connection_id={connection_id}")
        
        # Initialize session manager
        session_manager = SessionManager(DYNAMODB_TABLE_NAME, 24)
        
        # Retrieve session
        session = session_manager.get_session(session_id)
        if not session:
            ws_client.send_error(connection_id, "Session not found or expired", "SESSION_NOT_FOUND")
            return {'statusCode': 404}
        
        # Extract medical entities (with graceful degradation)
        ner_start = time.time()
        try:
            ner_client = MedicalNERClient()
            entities = ner_client.extract_entities(user_message)
            metrics['entity_count'] = len(entities)
        except Exception as e:
            logger.warning(f"Medical NER extraction failed: {e}")
            entities = []  # Continue without entities
        metrics['ner_processing_time'] = time.time() - ner_start
        
        # Create user message
        user_msg = Message(
            timestamp=datetime.now(timezone.utc).isoformat(),
            role=MessageRole.USER,
            content=user_message,
            extracted_entities=entities
        )
        
        # Append user message to session
        session_manager.append_message(session_id, user_msg)
        
        # Reload session to get updated state
        session = session_manager.get_session(session_id)
        
        # Check for emergency
        emergency_detector = EmergencyDetector()
        is_emergency = emergency_detector.detect_emergency(session.message_history)
        metrics['emergency_detected'] = is_emergency
        
        if is_emergency:
            session.emergency_detected = True
            session_manager.update_session(session)
        
        # Analyze context
        context_analyzer = ContextAnalyzer(session)
        context = context_analyzer.get_conversation_context()
        
        # Generate response using AI
        ai_start = time.time()
        try:
            # Build prompt
            prompt_builder = PromptBuilder(context, user_message)
            prompt = prompt_builder.build_prompt()
            
            # Generate response with Groq
            groq_client = GroqClient(GROQ_API_KEY, GROQ_MODEL)
            ai_response = groq_client.generate_response(prompt)
            
        except Exception as e:
            logger.error(f"Error generating AI response: {e}")
            ai_response = groq_client._get_fallback_response() if 'groq_client' in locals() else \
                "I'm unable to process your request at this time. Please seek in-person medical care."
        metrics['ai_response_time'] = time.time() - ai_start
        
        # Create assistant message
        assistant_msg = Message(
            timestamp=datetime.now(timezone.utc).isoformat(),
            role=MessageRole.ASSISTANT,
            content=ai_response,
            extracted_entities=[]
        )
        
        # Append assistant message to session
        session_manager.append_message(session_id, assistant_msg)
        
        # Increment follow-up count if we asked a question
        if "?" in ai_response and not is_emergency:
            session.follow_up_count += 1
            session_manager.update_session(session)
        
        # Send response to client
        response_message = {
            "type": "message",
            "timestamp": assistant_msg.timestamp,
            "content": ai_response,
            "conversationState": session.conversation_state.value,
            "severity": "SEVERE" if is_emergency else None
        }
        
        ws_client.send_message(connection_id, response_message)
        
        # Calculate total processing time
        metrics['total_processing_time'] = time.time() - start_time
        
        # Log conversation metrics (Requirement 14.1, 14.2)
        logger.info(
            "Message processed successfully",
            extra={
                "session_id": session_id,
                "connection_id": connection_id,
                "message_count": len(session.message_history),
                "entity_count": metrics['entity_count'],
                "emergency_detected": metrics['emergency_detected'],
                "ai_response_time_ms": int(metrics['ai_response_time'] * 1000),
                "ner_processing_time_ms": int(metrics['ner_processing_time'] * 1000),
                "total_processing_time_ms": int(metrics['total_processing_time'] * 1000),
                "message_length": metrics['message_length'],
                "follow_up_count": session.follow_up_count
            }
        )
        
        return {'statusCode': 200}
    
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in request body: {e}")
        ws_client.send_error(connection_id, "Invalid JSON format", "INVALID_JSON")
        return {'statusCode': 400}
    
    except Exception as e:
        logger.error(f"Error processing message: {e}", exc_info=True)
        ws_client.send_error(connection_id, "Internal server error", "INTERNAL_ERROR")
        return {'statusCode': 500}
