"""
Emergency Detector for identifying urgent medical situations
Validates Requirements 6.1, 6.2, 6.3, 6.7
"""

import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class EmergencyDetector:
    """
    Detects emergency situations from conversation messages.
    
    Validates Requirements:
    - 6.1: Check for emergency keywords in current and historical messages
    - 6.2: Immediately classify severity as SEVERE when emergency detected
    - 6.3: Recognize emergency patterns across multiple messages
    - 6.7: Log all emergency detections with full message history
    """
    
    # Emergency keywords that trigger immediate SEVERE classification
    EMERGENCY_KEYWORDS = [
        "chest pain",
        "stroke",
        "seizure",
        "severe bleeding",
        "difficulty breathing",
        "unconscious",
        "suicide"
    ]
    
    def __init__(self):
        """Initialize EmergencyDetector with predefined emergency keywords"""
        self.keywords = self.EMERGENCY_KEYWORDS
    
    def detect_emergency(self, message_history: List[Any]) -> bool:
        """
        Check current and historical messages for emergency patterns.
        
        Analyzes all messages in the conversation history to detect:
        1. Direct emergency keywords in any message
        2. Emergency patterns across multiple messages (e.g., "chest" + "pain")
        
        Args:
            message_history: List of Message objects from conversation session
        
        Returns:
            True if emergency detected, False otherwise
        
        Validates: Requirements 6.1, 6.2, 6.3
        """
        if not message_history:
            return False
        
        # Check each message for emergency keywords
        for message in message_history:
            message_text = message.content.lower()
            
            # Check for direct keyword matches
            for keyword in self.keywords:
                if keyword.lower() in message_text:
                    # Log emergency detection with context
                    self._log_emergency_detection(keyword, message_history)
                    return True
        
        # Check for emergency patterns across multiple messages
        # Example: "chest" in one message and "pain" in another
        if self._detect_cross_message_patterns(message_history):
            self._log_emergency_detection("cross-message pattern", message_history)
            return True
        
        return False
    
    def _detect_cross_message_patterns(self, message_history: List[Any]) -> bool:
        """
        Detect emergency patterns that span multiple messages.
        
        For example:
        - User: "I have chest discomfort"
        - Bot: "Can you describe it?"
        - User: "It's a sharp pain"
        
        This should detect "chest" + "pain" pattern.
        
        Args:
            message_history: List of Message objects
        
        Returns:
            True if cross-message emergency pattern detected
        
        Validates: Requirement 6.3
        """
        # Collect all user messages
        user_messages = [msg for msg in message_history if msg.role.value == "user"]
        
        if len(user_messages) < 2:
            return False
        
        # Combine all user message text
        combined_text = " ".join([msg.content.lower() for msg in user_messages])
        
        # Check if combined text contains emergency keywords
        for keyword in self.keywords:
            if keyword.lower() in combined_text:
                return True
        
        # Check for specific patterns like "chest" + "pain" across messages
        emergency_patterns = [
            ("chest", "pain"),
            ("difficulty", "breathing"),
            ("severe", "bleeding"),
            ("can't", "breathe"),
            ("cannot", "breathe")
        ]
        
        for pattern in emergency_patterns:
            word1, word2 = pattern
            # Check if both words appear in the combined text
            if word1 in combined_text and word2 in combined_text:
                return True
        
        return False
    
    def _log_emergency_detection(self, keyword: str, message_history: List[Any]) -> None:
        """
        Log emergency detection with full message history for audit.
        
        Args:
            keyword: The emergency keyword or pattern that was detected
            message_history: Complete message history for context
        
        Validates: Requirement 6.7
        """
        # Format message history for logging
        history_summary = []
        for i, msg in enumerate(message_history):
            history_summary.append({
                "index": i,
                "role": msg.role.value,
                "content": msg.content[:100],  # Truncate long messages
                "timestamp": msg.timestamp
            })
        
        logger.warning(
            f"EMERGENCY DETECTED: keyword='{keyword}', "
            f"message_count={len(message_history)}, "
            f"history={history_summary}"
        )
