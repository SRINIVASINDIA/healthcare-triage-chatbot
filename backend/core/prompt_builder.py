"""
Prompt Builder for constructing AI prompts with conversation context
Validates Requirements 13.1, 13.2, 13.3, 13.4, 13.5, 13.6, 13.7
"""

from typing import Dict, Any, List


class PromptBuilder:
    """
    Constructs AI prompts with conversation history and medical context.
    
    Validates Requirements:
    - 13.1: Include complete message history in prompts
    - 13.2: Format prompts with clear role labels (User:, Assistant:)
    - 13.3: Include system message instructing AI to act as medical triage assistant
    - 13.4: Include extracted medical entities as structured context
    - 13.5: Instruct AI to ask follow-up questions when information insufficient
    - 13.6: Instruct AI to provide triage assessment when sufficient information gathered
    - 13.7: Limit prompt size to 4000 tokens to stay within model context windows
    """
    
    # Approximate tokens per character (rough estimate: 1 token ≈ 4 characters)
    CHARS_PER_TOKEN = 4
    MAX_TOKENS = 4000
    MAX_CHARS = MAX_TOKENS * CHARS_PER_TOKEN  # 16000 characters
    
    def __init__(self, context: Dict[str, Any], current_message: str):
        """
        Initialize PromptBuilder with conversation context and current message.
        
        Args:
            context: Dictionary containing conversation context from ContextAnalyzer
            current_message: The current user message to respond to
        """
        self.context = context
        self.current_message = current_message
    
    def build_prompt(self) -> str:
        """
        Build complete prompt for AI model.
        
        Constructs a prompt that includes:
        1. System message with triage assistant instructions
        2. Formatted message history with role labels
        3. Extracted medical entities as structured context
        4. Current message
        5. Instructions for follow-up questions or triage assessment
        
        Returns:
            Complete prompt string ready for AI model
        
        Validates: Requirements 13.1, 13.2, 13.3, 13.4, 13.5, 13.6, 13.7
        """
        # Build prompt components
        system_message = self.get_system_message()
        message_history = self.format_message_history()
        entities_context = self.format_entities()
        
        # Construct full prompt
        prompt = f"""{system_message}

CONVERSATION HISTORY:
{message_history}

EXTRACTED MEDICAL INFORMATION:
{entities_context}

CURRENT MESSAGE:
{self.current_message}

INSTRUCTIONS:
{self._get_response_instructions()}

Respond to the current message:"""
        
        # Limit prompt size to stay within token limits
        if len(prompt) > self.MAX_CHARS:
            prompt = self._truncate_prompt(prompt)
        
        return prompt
    
    def format_message_history(self) -> str:
        """
        Format message history for prompt with role labels.
        
        Formats each message with "User:" or "Assistant:" prefix for clarity.
        
        Returns:
            Formatted message history string
        
        Validates: Requirements 13.1, 13.2
        """
        recent_messages = self.context.get("recent_messages", [])
        
        if not recent_messages:
            return "(No previous messages)"
        
        formatted_messages = []
        for message in recent_messages:
            role = message.get("role", "user")
            content = message.get("content", "")
            
            # Format with role label
            role_label = "User" if role == "user" else "Assistant"
            formatted_messages.append(f"{role_label}: {content}")
        
        return "\n".join(formatted_messages)
    
    def format_entities(self) -> str:
        """
        Format extracted entities for prompt as structured context.
        
        Presents medical entities in a clear, structured format for the AI.
        
        Returns:
            Formatted entities string
        
        Validates: Requirements 13.4
        """
        entities = self.context.get("aggregated_entities", {})
        
        formatted_parts = []
        
        # Format symptoms
        symptoms = entities.get("symptoms", [])
        if symptoms:
            formatted_parts.append(f"- Symptoms: {', '.join(symptoms)}")
        
        # Format body locations
        anatomy = entities.get("anatomy", [])
        if anatomy:
            formatted_parts.append(f"- Body Location: {', '.join(anatomy)}")
        
        # Format duration/time
        time_expressions = entities.get("time_expressions", [])
        if time_expressions:
            formatted_parts.append(f"- Duration: {', '.join(time_expressions)}")
        
        # Format medications
        medications = entities.get("medications", [])
        if medications:
            formatted_parts.append(f"- Medications: {', '.join(medications)}")
        
        # Format conditions
        conditions = entities.get("conditions", [])
        if conditions:
            formatted_parts.append(f"- Medical Conditions: {', '.join(conditions)}")
        
        if not formatted_parts:
            return "(No medical entities extracted yet)"
        
        return "\n".join(formatted_parts)
    
    def get_system_message(self) -> str:
        """
        Get system instruction for AI to act as medical triage assistant.
        
        Returns:
            System message string with triage assistant instructions
        
        Validates: Requirements 13.3
        """
        return """You are a medical triage assistant helping users assess their symptoms. You maintain conversation context and ask clarifying questions when needed.

Your role is to:
1. Gather information about symptoms, duration, severity, and location
2. Ask follow-up questions when information is insufficient
3. Provide triage assessment with severity level (LOW, MODERATE, SEVERE) when you have enough information
4. Be empathetic, professional, and clear in your responses
5. Reference previous information naturally in the conversation"""
    
    def _get_response_instructions(self) -> str:
        """
        Get instructions for the AI based on conversation state.
        
        Returns different instructions based on:
        - Whether emergency is detected
        - Whether ready for triage
        - Whether follow-up questions are needed
        
        Returns:
            Instructions string for AI response
        
        Validates: Requirements 13.5, 13.6
        """
        emergency_detected = self.context.get("emergency_detected", False)
        follow_up_count = self.context.get("follow_up_count", 0)
        
        if emergency_detected:
            return """EMERGENCY DETECTED: Provide immediate SEVERE classification and advise calling 911 or going to emergency room immediately. Do not ask follow-up questions."""
        
        # Check if we have sufficient information for triage
        entities = self.context.get("aggregated_entities", {})
        has_symptoms = bool(entities.get("symptoms"))
        has_duration = bool(entities.get("time_expressions"))
        
        if has_symptoms and has_duration and follow_up_count >= 3:
            return """You have gathered sufficient information. Provide a triage assessment with:
1. Severity level: LOW, MODERATE, or SEVERE
2. Recommended action (e.g., rest at home, see doctor within 24-48 hours, seek immediate care)
3. Brief explanation of your assessment"""
        
        if follow_up_count < 3:
            return """Ask ONE clarifying follow-up question to gather missing information:
- If duration is missing: Ask how long they've had the symptoms
- If severity is missing: Ask about the severity (scale of 1-10 or descriptive)
- If location is missing for location-dependent symptoms: Ask where they're experiencing it
- If only one symptom mentioned: Ask about other associated symptoms

Keep your question natural and empathetic."""
        
        return """Provide a triage assessment based on the information available, even if some details are missing."""
    
    def _truncate_prompt(self, prompt: str) -> str:
        """
        Truncate prompt to stay within token limits.
        
        Prioritizes keeping:
        1. System message (always keep)
        2. Current message (always keep)
        3. Recent messages (truncate oldest first)
        4. Entities (keep if space allows)
        
        Args:
            prompt: The full prompt that exceeds limits
        
        Returns:
            Truncated prompt within token limits
        
        Validates: Requirement 13.7
        """
        # If prompt is already within limits, return as is
        if len(prompt) <= self.MAX_CHARS:
            return prompt
        
        # Extract components
        system_message = self.get_system_message()
        entities_context = self.format_entities()
        instructions = self._get_response_instructions()
        
        # Calculate space for message history
        # Add extra buffer for formatting (600 chars)
        fixed_parts_length = len(system_message) + len(self.current_message) + len(entities_context) + len(instructions) + 600
        available_for_history = self.MAX_CHARS - fixed_parts_length
        
        # Get recent messages and truncate if needed
        recent_messages = self.context.get("recent_messages", [])
        
        if available_for_history > 0:
            # Keep as many recent messages as fit
            truncated_history = []
            current_length = 0
            
            # Start from most recent and work backwards
            for message in reversed(recent_messages):
                role = message.get("role", "user")
                content = message.get("content", "")
                role_label = "User" if role == "user" else "Assistant"
                formatted = f"{role_label}: {content}"
                
                if current_length + len(formatted) + 1 <= available_for_history:
                    truncated_history.insert(0, formatted)
                    current_length += len(formatted) + 1
                else:
                    break
            
            message_history = "\n".join(truncated_history) if truncated_history else "(History truncated)"
        else:
            message_history = "(History truncated due to length)"
        
        # Rebuild prompt with truncated history
        prompt = f"""{system_message}

CONVERSATION HISTORY:
{message_history}

EXTRACTED MEDICAL INFORMATION:
{entities_context}

CURRENT MESSAGE:
{self.current_message}

INSTRUCTIONS:
{instructions}

Respond to the current message:"""
        
        # Final safety check - if still too long, truncate message history more aggressively
        if len(prompt) > self.MAX_CHARS:
            message_history = "(History truncated due to length)"
            prompt = f"""{system_message}

CONVERSATION HISTORY:
{message_history}

EXTRACTED MEDICAL INFORMATION:
{entities_context}

CURRENT MESSAGE:
{self.current_message}

INSTRUCTIONS:
{instructions}

Respond to the current message:"""
        
        return prompt
