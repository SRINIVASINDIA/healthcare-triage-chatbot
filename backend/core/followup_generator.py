"""
Follow-Up Generator for intelligent clarification questions
Validates Requirements 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7
"""

from typing import Dict, Any, Optional


class FollowUpGenerator:
    """
    Generates follow-up questions to gather missing information for triage.
    
    Validates Requirements:
    - 5.1: Determine if clarification is needed for vague symptom descriptions
    - 5.2: Ask about symptom duration if TIME_EXPRESSION entities not present
    - 5.3: Ask about symptom severity if no severity descriptors found
    - 5.4: Ask about symptom location if ANATOMY entities missing
    - 5.5: Ask about associated symptoms if only one symptom mentioned
    - 5.6: Limit follow-up questions to maximum of 3 per conversation
    - 5.7: Provide triage assessment when sufficient information gathered
    """
    
    def __init__(self, context: Dict[str, Any], max_followups: int = 3):
        """
        Initialize FollowUpGenerator with conversation context.
        
        Args:
            context: Dictionary containing conversation context from ContextAnalyzer
            max_followups: Maximum number of follow-up questions allowed (default: 3)
        """
        self.context = context
        self.max_followups = max_followups
    
    def should_ask_followup(self) -> bool:
        """
        Determine if a follow-up question is needed.
        
        Returns True if:
        1. Follow-up count is less than max_followups
        2. There is missing information (duration, severity, location, or associated symptoms)
        3. Not in an emergency situation
        
        Returns:
            True if follow-up question should be asked, False otherwise
        
        Validates: Requirements 5.1, 5.6
        """
        # Check if we've reached the maximum follow-up count
        if self.context.get("follow_up_count", 0) >= self.max_followups:
            return False
        
        # Don't ask follow-ups if emergency detected
        if self.context.get("emergency_detected", False):
            return False
        
        # Check if there's missing information
        entities = self.context.get("aggregated_entities", {})
        
        # Check for missing time expressions (duration)
        if not entities.get("time_expressions"):
            return True
        
        # Check for missing severity descriptors
        # (We'll check if any symptom has severity info in the message content)
        if not self._has_severity_info():
            return True
        
        # Check for missing anatomy (location) for location-dependent symptoms
        if self._needs_location_info():
            return True
        
        # Check if only one symptom mentioned (need associated symptoms)
        symptoms = entities.get("symptoms", [])
        if len(symptoms) == 1:
            return True
        
        return False
    
    def generate_followup_question(self) -> Optional[str]:
        """
        Generate appropriate follow-up question based on missing information.
        
        Priority order:
        1. Duration (if missing time expressions)
        2. Severity (if no severity descriptors)
        3. Location (if missing anatomy for location-dependent symptoms)
        4. Associated symptoms (if only one symptom)
        
        Returns:
            Follow-up question string, or None if no follow-up needed
        
        Validates: Requirements 5.2, 5.3, 5.4, 5.5
        """
        if not self.should_ask_followup():
            return None
        
        entities = self.context.get("aggregated_entities", {})
        
        # Priority 1: Ask about duration
        if not entities.get("time_expressions"):
            symptoms = entities.get("symptoms", [])
            if symptoms:
                return f"How long have you been experiencing {symptoms[0]}?"
            else:
                return "How long have you been experiencing these symptoms?"
        
        # Priority 2: Ask about severity
        if not self._has_severity_info():
            symptoms = entities.get("symptoms", [])
            if symptoms:
                return f"On a scale of 1-10, how severe is your {symptoms[0]}?"
            else:
                return "How severe are your symptoms?"
        
        # Priority 3: Ask about location
        if self._needs_location_info():
            symptoms = entities.get("symptoms", [])
            if symptoms:
                return f"Where exactly are you experiencing the {symptoms[0]}?"
            else:
                return "Where are you experiencing the symptoms?"
        
        # Priority 4: Ask about associated symptoms
        symptoms = entities.get("symptoms", [])
        if len(symptoms) == 1:
            return f"Are you experiencing any other symptoms besides {symptoms[0]}?"
        
        return None
    
    def is_ready_for_triage(self) -> bool:
        """
        Check if sufficient information has been gathered for triage assessment.
        
        Considers information sufficient if:
        1. We have at least one symptom
        2. We have duration information (time expressions)
        3. We have severity information OR we've asked max follow-ups
        4. We have location information (if needed) OR we've asked max follow-ups
        
        Returns:
            True if ready for triage, False if more information needed
        
        Validates: Requirements 5.7
        """
        entities = self.context.get("aggregated_entities", {})
        follow_up_count = self.context.get("follow_up_count", 0)
        
        # Must have at least one symptom
        symptoms = entities.get("symptoms", [])
        if not symptoms:
            return False
        
        # If we've reached max follow-ups, we're ready (even if info incomplete)
        if follow_up_count >= self.max_followups:
            return True
        
        # Check if we have essential information
        has_duration = bool(entities.get("time_expressions"))
        has_severity = self._has_severity_info()
        has_location = not self._needs_location_info() or bool(entities.get("anatomy"))
        
        # Ready if we have duration and either severity or location
        return has_duration and (has_severity or has_location)
    
    def _has_severity_info(self) -> bool:
        """
        Check if severity information is present in the conversation.
        
        Looks for severity descriptors in recent messages like:
        - "severe", "mild", "moderate"
        - "sharp", "dull", "throbbing"
        - Numbers (1-10 scale)
        
        Returns:
            True if severity information found, False otherwise
        """
        severity_keywords = [
            "severe", "mild", "moderate", "intense", "slight",
            "sharp", "dull", "throbbing", "aching", "burning",
            "unbearable", "tolerable", "manageable"
        ]
        
        recent_messages = self.context.get("recent_messages", [])
        
        for message in recent_messages:
            content = message.get("content", "").lower()
            
            # Check for severity keywords
            for keyword in severity_keywords:
                if keyword in content:
                    return True
            
            # Check for numeric severity (1-10 scale)
            # Look for patterns like "7 out of 10", "8/10", "pain level 5"
            import re
            if re.search(r'\b([1-9]|10)\s*(out of|/)\s*10\b', content):
                return True
            if re.search(r'(pain|severity|level)\s*([1-9]|10)\b', content):
                return True
        
        return False
    
    def _needs_location_info(self) -> bool:
        """
        Check if location information is needed based on symptoms.
        
        Some symptoms are location-dependent (e.g., "pain" needs location),
        while others are not (e.g., "fever" doesn't need location).
        
        Returns:
            True if location information is needed, False otherwise
        """
        location_dependent_symptoms = [
            "pain", "ache", "discomfort", "swelling", "rash",
            "numbness", "tingling", "burning", "itching"
        ]
        
        entities = self.context.get("aggregated_entities", {})
        symptoms = entities.get("symptoms", [])
        anatomy = entities.get("anatomy", [])
        
        # If we already have anatomy information, location is not needed
        if anatomy:
            return False
        
        # Check if any symptom is location-dependent
        for symptom in symptoms:
            symptom_lower = symptom.lower()
            for location_symptom in location_dependent_symptoms:
                if location_symptom in symptom_lower:
                    return True
        
        return False
