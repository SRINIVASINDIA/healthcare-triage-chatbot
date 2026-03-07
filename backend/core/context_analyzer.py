"""
Context Analyzer for conversation intelligence
Extracts context from message history for response generation
"""

from typing import Dict, List, Any, Optional
import re


class ContextAnalyzer:
    """
    Analyzes conversation history to extract context for response generation.
    
    Validates Requirements:
    - 3.1: Retrieve complete message history from conversation session
    - 3.2: Extract all medical entities from previous messages
    - 3.5: Infer references from pronouns to previous entities
    - 4.4: Aggregate medical entities across all messages
    - 4.5: Reference aggregated medical entities in context
    """
    
    def __init__(self, session):
        """
        Initialize ContextAnalyzer with a conversation session.
        
        Args:
            session: ConversationSession object containing message history
        """
        self.session = session
    
    def get_conversation_context(self) -> Dict[str, Any]:
        """
        Extract structured context from message history.
        
        Returns a dictionary containing:
        - recent_messages: Last N messages for prompt construction
        - aggregated_entities: All medical entities from conversation
        - conversation_state: Current state of the conversation
        - follow_up_count: Number of follow-up questions asked
        - emergency_detected: Whether emergency was detected
        - inferred_references: Empty dict (populated when analyzing specific message)
        
        Validates: Requirements 3.1, 3.2, 4.4, 4.5
        """
        return {
            "recent_messages": self.get_recent_messages(),
            "aggregated_entities": self.get_aggregated_entities(),
            "conversation_state": self.session.conversation_state.value,
            "follow_up_count": self.session.follow_up_count,
            "emergency_detected": self.session.emergency_detected,
            "inferred_references": {}
        }
    
    def get_recent_messages(self, count: int = 10) -> List[Dict[str, Any]]:
        """
        Get last N messages for prompt construction.
        
        Args:
            count: Number of recent messages to retrieve (default: 10)
        
        Returns:
            List of message dictionaries with timestamp, role, and content
        
        Validates: Requirements 3.1, 3.4
        """
        # Get the last N messages from message history
        recent_messages = self.session.message_history[-count:] if self.session.message_history else []
        
        # Convert to dictionary format
        return [
            {
                "timestamp": msg.timestamp,
                "role": msg.role.value,
                "content": msg.content
            }
            for msg in recent_messages
        ]
    
    def get_aggregated_entities(self) -> Dict[str, List[str]]:
        """
        Get all medical entities mentioned in conversation.
        
        Returns a dictionary with entity types as keys and lists of unique entity texts as values:
        - symptoms: List of symptom entities
        - anatomy: List of anatomy/body location entities
        - medications: List of medication entities
        - conditions: List of medical condition entities
        - time_expressions: List of time/duration entities
        
        Validates: Requirements 3.2, 4.4, 4.5
        """
        # Return the pre-aggregated entities from the session
        # These are maintained by the SessionManager when messages are appended
        return self.session.aggregated_entities
    
    def infer_references(self, current_message: str) -> Dict[str, str]:
        """
        Resolve pronouns and references to previous entities.
        
        Analyzes the current message for pronouns and vague references like:
        - "it" -> most recent symptom or condition
        - "the pain" -> most recent symptom containing "pain"
        - "there" -> most recent anatomy location
        
        Args:
            current_message: The current user message to analyze
        
        Returns:
            Dictionary mapping references to their inferred entities
            Example: {"it": "headache", "the pain": "chest pain"}
        
        Validates: Requirements 3.5
        """
        inferred = {}
        message_lower = current_message.lower()
        
        # Get aggregated entities for reference resolution
        entities = self.get_aggregated_entities()
        
        # Infer "it" reference - map to most recent symptom or condition
        if re.search(r'\bit\b', message_lower):
            # Try symptoms first, then conditions
            if entities.get("symptoms"):
                inferred["it"] = entities["symptoms"][-1]
            elif entities.get("conditions"):
                inferred["it"] = entities["conditions"][-1]
        
        # Infer "the pain" reference - map to most recent pain-related symptom
        if re.search(r'\bthe pain\b', message_lower):
            if entities.get("symptoms"):
                # Find the most recent symptom containing "pain"
                pain_symptoms = [s for s in entities["symptoms"] if "pain" in s.lower()]
                if pain_symptoms:
                    inferred["the pain"] = pain_symptoms[-1]
                else:
                    # Fall back to most recent symptom
                    inferred["the pain"] = entities["symptoms"][-1]
        
        # Infer "there" reference - map to most recent anatomy location
        if re.search(r'\bthere\b', message_lower):
            if entities.get("anatomy"):
                inferred["there"] = entities["anatomy"][-1]
        
        # Infer "that" reference - map to most recent symptom or condition
        if re.search(r'\bthat\b', message_lower):
            if entities.get("symptoms"):
                inferred["that"] = entities["symptoms"][-1]
            elif entities.get("conditions"):
                inferred["that"] = entities["conditions"][-1]
        
        return inferred
