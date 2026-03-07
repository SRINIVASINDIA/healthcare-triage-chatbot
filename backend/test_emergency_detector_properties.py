"""
Property-based tests for EmergencyDetector
Tests universal properties for emergency detection across randomized inputs
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from datetime import datetime, timezone
from backend.core.models import Message, MessageRole
from backend.core.emergency_detector import EmergencyDetector


# Strategy for generating messages
@st.composite
def message_strategy(draw, content=None):
    """Generate random messages"""
    role = draw(st.sampled_from([MessageRole.USER, MessageRole.ASSISTANT]))
    if content is None:
        content = draw(st.text(min_size=1, max_size=200))
    timestamp = datetime.now(timezone.utc).isoformat()
    
    return Message(
        timestamp=timestamp,
        role=role,
        content=content,
        extracted_entities=[]
    )


# Feature: chatgpt-like-enhancements, Property 18: Emergency Detection Across Messages
# Validates: Requirements 6.1, 6.2
@settings(max_examples=100)
@given(
    emergency_keyword=st.sampled_from(EmergencyDetector.EMERGENCY_KEYWORDS),
    num_messages_before=st.integers(min_value=0, max_value=5),
    num_messages_after=st.integers(min_value=0, max_value=5)
)
def test_emergency_detection_across_messages(emergency_keyword, num_messages_before, num_messages_after):
    """
    For any session where emergency keywords appear in any message (current or historical),
    the backend should detect the emergency and classify severity as SEVERE.
    """
    # Arrange
    detector = EmergencyDetector()
    
    # Create messages before the emergency message
    message_history = []
    for i in range(num_messages_before):
        msg = Message(
            timestamp=datetime.now(timezone.utc).isoformat(),
            role=MessageRole.USER if i % 2 == 0 else MessageRole.ASSISTANT,
            content=f"This is message {i} without emergency keywords",
            extracted_entities=[]
        )
        message_history.append(msg)
    
    # Add emergency message
    emergency_msg = Message(
        timestamp=datetime.now(timezone.utc).isoformat(),
        role=MessageRole.USER,
        content=f"I am experiencing {emergency_keyword} right now",
        extracted_entities=[]
    )
    message_history.append(emergency_msg)
    
    # Add messages after the emergency message
    for i in range(num_messages_after):
        msg = Message(
            timestamp=datetime.now(timezone.utc).isoformat(),
            role=MessageRole.USER if i % 2 == 0 else MessageRole.ASSISTANT,
            content=f"This is follow-up message {i}",
            extracted_entities=[]
        )
        message_history.append(msg)
    
    # Act
    is_emergency = detector.detect_emergency(message_history)
    
    # Assert - emergency should be detected regardless of position
    assert is_emergency is True, f"Emergency keyword '{emergency_keyword}' should be detected"


# Feature: chatgpt-like-enhancements, Property 18: Emergency Detection - Cross-Message Patterns
# Validates: Requirements 6.1, 6.2, 6.3
@settings(max_examples=100)
@given(
    pattern=st.sampled_from([
        ("chest", "pain"),
        ("difficulty", "breathing"),
        ("severe", "bleeding"),
        ("can't", "breathe"),
        ("cannot", "breathe")
    ]),
    messages_between=st.integers(min_value=0, max_value=3)
)
def test_emergency_detection_cross_message_patterns(pattern, messages_between):
    """
    For any session where emergency patterns appear across multiple messages,
    the backend should detect the emergency.
    
    Example: "chest" in message 1, "pain" in message 3
    """
    # Arrange
    detector = EmergencyDetector()
    word1, word2 = pattern
    
    # Create message with first word
    message_history = [
        Message(
            timestamp=datetime.now(timezone.utc).isoformat(),
            role=MessageRole.USER,
            content=f"I have {word1} discomfort",
            extracted_entities=[]
        )
    ]
    
    # Add messages in between
    for i in range(messages_between):
        msg = Message(
            timestamp=datetime.now(timezone.utc).isoformat(),
            role=MessageRole.ASSISTANT if i % 2 == 0 else MessageRole.USER,
            content=f"Can you describe it more? Message {i}",
            extracted_entities=[]
        )
        message_history.append(msg)
    
    # Add message with second word
    message_history.append(
        Message(
            timestamp=datetime.now(timezone.utc).isoformat(),
            role=MessageRole.USER,
            content=f"It's a sharp {word2}",
            extracted_entities=[]
        )
    )
    
    # Act
    is_emergency = detector.detect_emergency(message_history)
    
    # Assert - emergency pattern should be detected across messages
    assert is_emergency is True, f"Emergency pattern '{word1}' + '{word2}' should be detected across messages"


# Feature: chatgpt-like-enhancements, Property 19: Emergency Response Priority
# Validates: Requirements 6.5
@settings(max_examples=100)
@given(
    emergency_keyword=st.sampled_from(EmergencyDetector.EMERGENCY_KEYWORDS)
)
def test_emergency_detection_returns_true_immediately(emergency_keyword):
    """
    For any session where an emergency is detected, the detect_emergency method
    should return True immediately, indicating that an immediate SEVERE response
    should be sent without asking follow-up questions.
    """
    # Arrange
    detector = EmergencyDetector()
    
    # Create a single message with emergency keyword
    message_history = [
        Message(
            timestamp=datetime.now(timezone.utc).isoformat(),
            role=MessageRole.USER,
            content=f"Help! I have {emergency_keyword}!",
            extracted_entities=[]
        )
    ]
    
    # Act
    is_emergency = detector.detect_emergency(message_history)
    
    # Assert - should return True immediately
    assert is_emergency is True, f"Emergency keyword '{emergency_keyword}' should trigger immediate detection"


# Test: No false positives for non-emergency messages
@settings(max_examples=100)
@given(
    num_messages=st.integers(min_value=1, max_value=10)
)
def test_no_false_positives_for_normal_messages(num_messages):
    """
    For any session with normal (non-emergency) messages,
    the detector should not falsely detect an emergency.
    """
    # Arrange
    detector = EmergencyDetector()
    
    # Create messages without emergency keywords
    safe_phrases = [
        "I have a headache",
        "My stomach hurts",
        "I feel tired",
        "I have a fever",
        "My back aches",
        "I have a cough",
        "I feel dizzy",
        "I have a rash"
    ]
    
    message_history = []
    for i in range(num_messages):
        msg = Message(
            timestamp=datetime.now(timezone.utc).isoformat(),
            role=MessageRole.USER if i % 2 == 0 else MessageRole.ASSISTANT,
            content=safe_phrases[i % len(safe_phrases)],
            extracted_entities=[]
        )
        message_history.append(msg)
    
    # Act
    is_emergency = detector.detect_emergency(message_history)
    
    # Assert - should not detect emergency
    assert is_emergency is False, "Normal messages should not trigger emergency detection"


# Test: Case-insensitive detection
@settings(max_examples=100)
@given(
    emergency_keyword=st.sampled_from(EmergencyDetector.EMERGENCY_KEYWORDS),
    case_variant=st.sampled_from(["lower", "upper", "title", "mixed"])
)
def test_case_insensitive_emergency_detection(emergency_keyword, case_variant):
    """
    Emergency detection should be case-insensitive.
    """
    # Arrange
    detector = EmergencyDetector()
    
    # Transform keyword based on case variant
    if case_variant == "lower":
        keyword = emergency_keyword.lower()
    elif case_variant == "upper":
        keyword = emergency_keyword.upper()
    elif case_variant == "title":
        keyword = emergency_keyword.title()
    else:  # mixed
        keyword = "".join([c.upper() if i % 2 == 0 else c.lower() 
                          for i, c in enumerate(emergency_keyword)])
    
    message_history = [
        Message(
            timestamp=datetime.now(timezone.utc).isoformat(),
            role=MessageRole.USER,
            content=f"I am experiencing {keyword}",
            extracted_entities=[]
        )
    ]
    
    # Act
    is_emergency = detector.detect_emergency(message_history)
    
    # Assert - should detect regardless of case
    assert is_emergency is True, f"Emergency keyword '{keyword}' should be detected regardless of case"


# Test: Empty message history
def test_empty_message_history_no_emergency():
    """
    For an empty message history, no emergency should be detected.
    """
    # Arrange
    detector = EmergencyDetector()
    message_history = []
    
    # Act
    is_emergency = detector.detect_emergency(message_history)
    
    # Assert
    assert is_emergency is False, "Empty message history should not trigger emergency detection"


# Test: Emergency keyword in assistant message (should still detect)
@settings(max_examples=100)
@given(
    emergency_keyword=st.sampled_from(EmergencyDetector.EMERGENCY_KEYWORDS)
)
def test_emergency_detection_in_assistant_message(emergency_keyword):
    """
    Emergency keywords should be detected even in assistant messages
    (though this is unlikely in practice).
    """
    # Arrange
    detector = EmergencyDetector()
    
    message_history = [
        Message(
            timestamp=datetime.now(timezone.utc).isoformat(),
            role=MessageRole.ASSISTANT,
            content=f"Are you experiencing {emergency_keyword}?",
            extracted_entities=[]
        )
    ]
    
    # Act
    is_emergency = detector.detect_emergency(message_history)
    
    # Assert - should detect in any message
    assert is_emergency is True, f"Emergency keyword '{emergency_keyword}' should be detected in assistant messages too"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
