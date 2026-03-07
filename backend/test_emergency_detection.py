"""
Unit tests for emergency detection functionality
Tests Task 4.1: Emergency keyword detection and response
"""

import json
import pytest
from lambda_function import (
    lambda_handler,
    detect_emergency,
    create_emergency_response,
    EMERGENCY_KEYWORDS
)


class MockContext:
    """Mock Lambda context for testing"""
    def __init__(self, request_id='test-request-id'):
        self.request_id = request_id
        self.function_name = 'test-function'
        self.memory_limit_in_mb = 128


class TestEmergencyKeywordDetection:
    """Test emergency keyword detection - Requirements 1.1, 1.2"""
    
    def test_detect_chest_pain(self):
        """Test detection of 'chest pain' keyword"""
        assert detect_emergency("I have chest pain") is True
        assert detect_emergency("experiencing chest pain right now") is True
    
    def test_detect_stroke(self):
        """Test detection of 'stroke' keyword"""
        assert detect_emergency("I think I'm having a stroke") is True
        assert detect_emergency("stroke symptoms") is True
    
    def test_detect_seizure(self):
        """Test detection of 'seizure' keyword"""
        assert detect_emergency("having a seizure") is True
        assert detect_emergency("seizure episode") is True
    
    def test_detect_severe_bleeding(self):
        """Test detection of 'severe bleeding' keyword"""
        assert detect_emergency("severe bleeding from wound") is True
        assert detect_emergency("I have severe bleeding") is True
    
    def test_detect_difficulty_breathing(self):
        """Test detection of 'difficulty breathing' keyword"""
        assert detect_emergency("difficulty breathing") is True
        assert detect_emergency("having difficulty breathing") is True
    
    def test_detect_unconscious(self):
        """Test detection of 'unconscious' keyword"""
        assert detect_emergency("person is unconscious") is True
        assert detect_emergency("unconscious patient") is True
    
    def test_detect_suicide(self):
        """Test detection of 'suicide' keyword"""
        assert detect_emergency("thinking about suicide") is True
        assert detect_emergency("suicide thoughts") is True


class TestEmergencyKeywordsWithSurroundingText:
    """Test emergency keywords with surrounding text - Requirements 1.1, 1.2"""
    
    def test_keyword_at_beginning(self):
        """Test emergency keyword at the beginning of text"""
        assert detect_emergency("chest pain and shortness of breath") is True
    
    def test_keyword_at_end(self):
        """Test emergency keyword at the end of text"""
        assert detect_emergency("I am experiencing chest pain") is True
    
    def test_keyword_in_middle(self):
        """Test emergency keyword in the middle of text"""
        assert detect_emergency("I have been having chest pain for an hour") is True
    
    def test_keyword_with_punctuation(self):
        """Test emergency keyword with punctuation"""
        assert detect_emergency("chest pain! Help!") is True
        assert detect_emergency("chest pain, nausea, sweating") is True
    
    def test_keyword_in_sentence(self):
        """Test emergency keyword in a complete sentence"""
        assert detect_emergency("My father is having a stroke and needs help") is True
        assert detect_emergency("The patient has severe bleeding from the leg") is True


class TestCaseInsensitiveMatching:
    """Test case-insensitive emergency keyword matching - Requirements 1.1, 1.2"""
    
    def test_lowercase_keywords(self):
        """Test lowercase emergency keywords"""
        assert detect_emergency("chest pain") is True
        assert detect_emergency("stroke") is True
        assert detect_emergency("seizure") is True
    
    def test_uppercase_keywords(self):
        """Test uppercase emergency keywords"""
        assert detect_emergency("CHEST PAIN") is True
        assert detect_emergency("STROKE") is True
        assert detect_emergency("SEIZURE") is True
    
    def test_mixed_case_keywords(self):
        """Test mixed case emergency keywords"""
        assert detect_emergency("Chest Pain") is True
        assert detect_emergency("ChEsT pAiN") is True
        assert detect_emergency("Stroke") is True
        assert detect_emergency("SEVERE BLEEDING") is True
    
    def test_title_case_keywords(self):
        """Test title case emergency keywords"""
        assert detect_emergency("Difficulty Breathing") is True
        assert detect_emergency("Severe Bleeding") is True


class TestMultipleKeywordsInInput:
    """Test multiple emergency keywords in one input - Requirements 1.1, 1.2"""
    
    def test_two_keywords(self):
        """Test input with two emergency keywords"""
        assert detect_emergency("chest pain and difficulty breathing") is True
        assert detect_emergency("stroke and seizure") is True
    
    def test_three_keywords(self):
        """Test input with three emergency keywords"""
        assert detect_emergency("chest pain, difficulty breathing, and unconscious") is True
    
    def test_multiple_keywords_mixed_case(self):
        """Test multiple keywords with mixed case"""
        assert detect_emergency("CHEST PAIN and difficulty breathing") is True
        assert detect_emergency("Stroke, SEIZURE, severe bleeding") is True


class TestNonEmergencySymptoms:
    """Test that non-emergency symptoms are not detected as emergencies"""
    
    def test_common_symptoms(self):
        """Test common non-emergency symptoms"""
        assert detect_emergency("headache") is False
        assert detect_emergency("fever") is False
        assert detect_emergency("cough") is False
        assert detect_emergency("sore throat") is False
    
    def test_partial_keyword_matches(self):
        """Test that partial matches don't trigger emergency detection"""
        assert detect_emergency("pain in chest area") is False  # "chest pain" not together
        assert detect_emergency("breathing normally") is False
        assert detect_emergency("conscious and alert") is False
    
    def test_similar_but_different_words(self):
        """Test words similar to emergency keywords"""
        assert detect_emergency("mild bleeding") is False  # not "severe bleeding"
        assert detect_emergency("easy breathing") is False


class TestEmergencyResponse:
    """Test emergency response creation - Requirements 1.1, 1.4"""
    
    def test_emergency_response_structure(self):
        """Test that emergency response has correct structure"""
        response = create_emergency_response()
        
        assert 'severity' in response
        assert 'advice' in response
    
    def test_emergency_response_severity(self):
        """Test that emergency response has SEVERE severity"""
        response = create_emergency_response()
        
        assert response['severity'] == 'SEVERE'
    
    def test_emergency_response_advice_content(self):
        """Test that emergency advice directs to call emergency services"""
        response = create_emergency_response()
        advice_lower = response['advice'].lower()
        
        # Should contain emergency-related terms
        emergency_terms = ['911', 'emergency', 'urgent', 'immediately']
        has_emergency_term = any(term in advice_lower for term in emergency_terms)
        
        assert has_emergency_term, \
            f"Emergency advice should contain emergency guidance, got: {response['advice']}"


class TestEmergencyEndToEnd:
    """Test end-to-end emergency detection through Lambda handler - Requirements 1.1, 1.2, 1.4"""
    
    def test_emergency_keyword_returns_severe(self):
        """Test that emergency keywords return SEVERE severity"""
        event = {
            'body': json.dumps({'symptoms': 'chest pain'})
        }
        
        response = lambda_handler(event, MockContext())
        body = json.loads(response['body'])
        
        assert response['statusCode'] == 200
        assert body['severity'] == 'SEVERE'
    
    def test_emergency_response_has_emergency_advice(self):
        """Test that emergency response includes emergency advice"""
        event = {
            'body': json.dumps({'symptoms': 'having a stroke'})
        }
        
        response = lambda_handler(event, MockContext())
        body = json.loads(response['body'])
        
        advice_lower = body['advice'].lower()
        emergency_terms = ['911', 'emergency', 'urgent', 'immediately']
        has_emergency_term = any(term in advice_lower for term in emergency_terms)
        
        assert has_emergency_term
    
    def test_all_emergency_keywords_trigger_severe(self):
        """Test that all emergency keywords trigger SEVERE response"""
        for keyword in EMERGENCY_KEYWORDS:
            event = {
                'body': json.dumps({'symptoms': f'I have {keyword}'})
            }
            
            response = lambda_handler(event, MockContext())
            body = json.loads(response['body'])
            
            assert body['severity'] == 'SEVERE', \
                f"Keyword '{keyword}' should trigger SEVERE severity"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
