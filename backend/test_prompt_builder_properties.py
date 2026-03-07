"""
Property-based tests for PromptBuilder
Tests universal properties for prompt construction across randomized inputs
"""

import pytest
from hypothesis import given, strategies as st, settings
from backend.core.prompt_builder import PromptBuilder


# Strategy for generating context
@st.composite
def context_strategy(draw):
    """Generate random conversation context"""
    # Generate aggregated entities
    num_symptoms = draw(st.integers(min_value=0, max_value=5))
    num_anatomy = draw(st.integers(min_value=0, max_value=3))
    num_time_expr = draw(st.integers(min_value=0, max_value=2))
    
    symptoms = [f"symptom_{i}" for i in range(num_symptoms)]
    anatomy = [f"body_part_{i}" for i in range(num_anatomy)]
    time_expressions = [f"{i+1} days" for i in range(num_time_expr)]
    
    # Generate recent messages
    num_messages = draw(st.integers(min_value=0, max_value=15))
    recent_messages = []
    for i in range(num_messages):
        recent_messages.append({
            "role": "user" if i % 2 == 0 else "assistant",
            "content": f"Message {i} content"
        })
    
    return {
        "aggregated_entities": {
            "symptoms": symptoms,
            "anatomy": anatomy,
            "time_expressions": time_expressions,
            "medications": [],
            "conditions": []
        },
        "recent_messages": recent_messages,
        "follow_up_count": draw(st.integers(min_value=0, max_value=3)),
        "emergency_detected": draw(st.booleans())
    }


# Feature: chatgpt-like-enhancements, Property 9: Prompt Contains Context
# Validates: Requirements 3.3, 13.4
@settings(max_examples=100)
@given(
    context=context_strategy(),
    current_message=st.text(min_size=1, max_size=200)
)
def test_prompt_contains_context(context, current_message):
    """
    For any AI request, the constructed prompt should include conversation context
    (recent messages and aggregated entities).
    """
    # Arrange
    builder = PromptBuilder(context, current_message)
    
    # Act
    prompt = builder.build_prompt()
    
    # Assert - prompt should be a non-empty string
    assert isinstance(prompt, str)
    assert len(prompt) > 0
    
    # Assert - prompt should contain the current message
    assert current_message in prompt
    
    # Assert - prompt should contain conversation history section
    assert "CONVERSATION HISTORY" in prompt or "conversation history" in prompt.lower()
    
    # Assert - prompt should contain medical information section
    assert "MEDICAL INFORMATION" in prompt or "medical" in prompt.lower()
    
    # Assert - if there are symptoms, they should be in the prompt
    symptoms = context.get("aggregated_entities", {}).get("symptoms", [])
    if symptoms:
        # At least one symptom should be mentioned
        assert any(symptom in prompt for symptom in symptoms)
    
    # Assert - if there are recent messages, some should be in the prompt
    recent_messages = context.get("recent_messages", [])
    if recent_messages:
        # At least one message content should be in the prompt
        assert any(msg["content"] in prompt for msg in recent_messages[-5:])  # Check last 5


# Feature: chatgpt-like-enhancements, Property 33: Prompt Formatting with Role Labels
# Validates: Requirements 13.2
@settings(max_examples=100)
@given(
    num_messages=st.integers(min_value=1, max_value=10)
)
def test_prompt_formatting_with_role_labels(num_messages):
    """
    For any AI prompt constructed from message history, each message should be
    prefixed with its role label ("User:" or "Assistant:").
    """
    # Arrange
    recent_messages = []
    for i in range(num_messages):
        recent_messages.append({
            "role": "user" if i % 2 == 0 else "assistant",
            "content": f"Test message {i}"
        })
    
    context = {
        "aggregated_entities": {
            "symptoms": ["headache"],
            "anatomy": [],
            "time_expressions": [],
            "medications": [],
            "conditions": []
        },
        "recent_messages": recent_messages,
        "follow_up_count": 0,
        "emergency_detected": False
    }
    
    builder = PromptBuilder(context, "Current message")
    
    # Act
    formatted_history = builder.format_message_history()
    
    # Assert - formatted history should contain role labels
    assert "User:" in formatted_history or "Assistant:" in formatted_history
    
    # Assert - each message should have a role label
    lines = formatted_history.split("\n")
    for line in lines:
        if line.strip() and not line.startswith("("):  # Skip empty lines and special messages
            # Each line should start with "User:" or "Assistant:"
            assert line.startswith("User:") or line.startswith("Assistant:")


# Feature: chatgpt-like-enhancements, Property 35: Prompt Size Limit
# Validates: Requirements 13.7
@settings(max_examples=100)
@given(
    num_messages=st.integers(min_value=10, max_value=50),
    message_length=st.integers(min_value=100, max_value=500)
)
def test_prompt_size_limit(num_messages, message_length):
    """
    For any constructed prompt, the total token count should not exceed 4000 tokens
    to stay within model context windows.
    
    We approximate: 1 token ≈ 4 characters, so max 16000 characters.
    """
    # Arrange - create a large context with many long messages
    recent_messages = []
    for i in range(num_messages):
        # Create long messages
        content = "x" * message_length
        recent_messages.append({
            "role": "user" if i % 2 == 0 else "assistant",
            "content": content
        })
    
    context = {
        "aggregated_entities": {
            "symptoms": ["symptom1", "symptom2", "symptom3"],
            "anatomy": ["location1", "location2"],
            "time_expressions": ["2 days", "3 hours"],
            "medications": ["med1", "med2"],
            "conditions": ["condition1"]
        },
        "recent_messages": recent_messages,
        "follow_up_count": 0,
        "emergency_detected": False
    }
    
    builder = PromptBuilder(context, "Current message")
    
    # Act
    prompt = builder.build_prompt()
    
    # Assert - prompt should not exceed maximum character limit
    max_chars = PromptBuilder.MAX_CHARS
    assert len(prompt) <= max_chars, f"Prompt length {len(prompt)} exceeds maximum {max_chars}"
    
    # Assert - prompt should still contain essential components even when truncated
    assert "CURRENT MESSAGE" in prompt or "current message" in prompt.lower()
    assert "Current message" in prompt  # The actual current message


# Test: System message is always included
@settings(max_examples=100)
@given(
    context=context_strategy(),
    current_message=st.text(min_size=1, max_size=100)
)
def test_system_message_always_included(context, current_message):
    """
    For any AI request, the prompt should include a system message instructing
    the AI to act as a medical triage assistant.
    """
    # Arrange
    builder = PromptBuilder(context, current_message)
    
    # Act
    prompt = builder.build_prompt()
    system_message = builder.get_system_message()
    
    # Assert - system message should be in the prompt
    assert system_message in prompt
    
    # Assert - system message should mention triage or medical assistant
    assert "triage" in system_message.lower() or "medical" in system_message.lower()


# Test: Emergency instructions when emergency detected
@settings(max_examples=100)
@given(
    current_message=st.text(min_size=1, max_size=100)
)
def test_emergency_instructions_when_emergency_detected(current_message):
    """
    When emergency is detected, the prompt should include instructions to
    provide immediate SEVERE classification without follow-up questions.
    """
    # Arrange
    context = {
        "aggregated_entities": {
            "symptoms": ["chest pain"],
            "anatomy": [],
            "time_expressions": [],
            "medications": [],
            "conditions": []
        },
        "recent_messages": [],
        "follow_up_count": 0,
        "emergency_detected": True  # Emergency!
    }
    
    builder = PromptBuilder(context, current_message)
    
    # Act
    prompt = builder.build_prompt()
    
    # Assert - prompt should contain emergency instructions
    assert "EMERGENCY" in prompt or "emergency" in prompt.lower()
    assert "SEVERE" in prompt or "severe" in prompt.lower()


# Test: Follow-up instructions when information insufficient
@settings(max_examples=100)
@given(
    follow_up_count=st.integers(min_value=0, max_value=2)
)
def test_followup_instructions_when_information_insufficient(follow_up_count):
    """
    When information is insufficient and follow-up count is below max,
    the prompt should include instructions to ask follow-up questions.
    """
    # Arrange
    context = {
        "aggregated_entities": {
            "symptoms": ["headache"],
            "anatomy": [],
            "time_expressions": [],  # Missing duration
            "medications": [],
            "conditions": []
        },
        "recent_messages": [],
        "follow_up_count": follow_up_count,
        "emergency_detected": False
    }
    
    builder = PromptBuilder(context, "I have a headache")
    
    # Act
    prompt = builder.build_prompt()
    
    # Assert - prompt should contain follow-up instructions
    if follow_up_count < 3:
        assert "follow-up" in prompt.lower() or "question" in prompt.lower()


# Test: Triage instructions when information sufficient
def test_triage_instructions_when_information_sufficient():
    """
    When sufficient information is gathered, the prompt should include
    instructions to provide triage assessment.
    """
    # Arrange
    context = {
        "aggregated_entities": {
            "symptoms": ["headache"],
            "anatomy": ["head"],
            "time_expressions": ["2 days"],  # Has duration
            "medications": [],
            "conditions": []
        },
        "recent_messages": [
            {"role": "user", "content": "I have a severe headache for 2 days"}
        ],
        "follow_up_count": 3,  # Max follow-ups reached
        "emergency_detected": False
    }
    
    builder = PromptBuilder(context, "It's getting worse")
    
    # Act
    prompt = builder.build_prompt()
    
    # Assert - prompt should contain triage instructions
    assert "triage" in prompt.lower() or "assessment" in prompt.lower()
    assert "severity" in prompt.lower() or "SEVERE" in prompt or "MODERATE" in prompt or "LOW" in prompt


# Test: Empty message history handling
def test_empty_message_history_handling():
    """
    When there are no previous messages, the prompt should handle it gracefully.
    """
    # Arrange
    context = {
        "aggregated_entities": {
            "symptoms": [],
            "anatomy": [],
            "time_expressions": [],
            "medications": [],
            "conditions": []
        },
        "recent_messages": [],  # Empty
        "follow_up_count": 0,
        "emergency_detected": False
    }
    
    builder = PromptBuilder(context, "I need help")
    
    # Act
    prompt = builder.build_prompt()
    formatted_history = builder.format_message_history()
    
    # Assert - should handle empty history gracefully
    assert isinstance(formatted_history, str)
    assert len(formatted_history) > 0
    assert "No previous messages" in formatted_history or formatted_history == ""


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
