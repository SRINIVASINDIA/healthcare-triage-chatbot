"""
WebSocket Client for sending messages to connected clients
Validates Requirement 2.5
"""

import json
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class WebSocketClient:
    """
    Client for sending messages to WebSocket connections via API Gateway.
    
    Validates Requirement 2.5: Send responses back to client through WebSocket connection
    """
    
    def __init__(self, api_gateway_management_api):
        """
        Initialize WebSocket client with API Gateway Management API.
        
        Args:
            api_gateway_management_api: boto3 API Gateway Management API client
        """
        self.api = api_gateway_management_api
    
    def send_message(self, connection_id: str, message: Dict[str, Any]) -> bool:
        """
        Send message to WebSocket connection.
        
        Args:
            connection_id: The WebSocket connection ID
            message: Dictionary message to send (will be JSON-encoded)
        
        Returns:
            True if message sent successfully, False otherwise
        
        Validates: Requirement 2.5
        """
        try:
            # Convert message to JSON
            data = json.dumps(message)
            
            # Send to connection
            self.api.post_to_connection(
                ConnectionId=connection_id,
                Data=data.encode('utf-8')
            )
            
            logger.info(f"Message sent to connection {connection_id}")
            return True
        
        except self.api.exceptions.GoneException:
            # Connection no longer exists
            logger.info(f"Connection {connection_id} no longer exists (GoneException)")
            return False
        
        except Exception as e:
            logger.error(f"Error sending message to connection {connection_id}: {e}")
            return False
    
    def send_error(self, connection_id: str, error_message: str, error_code: str = "ERROR") -> bool:
        """
        Send error response to WebSocket connection.
        
        Args:
            connection_id: The WebSocket connection ID
            error_message: User-friendly error message
            error_code: Error code identifier
        
        Returns:
            True if error sent successfully, False otherwise
        """
        error_response = {
            "type": "error",
            "message": error_message,
            "code": error_code
        }
        
        return self.send_message(connection_id, error_response)
