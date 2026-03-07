"""
Unit tests for FollowUpGenerator
Tests specific examples and edge cases for follow-up question generation
"""

import pytest
from backend.core.followup_generator import FollowUpGenerator


class TestFollowUpGenerationForMissingDuration:
    """Test follow-up generation for missing duration - Requirement 5.2"""
    
    def test_asks_about_duration_when_missing(self):
        """Should ask about duration when time expressions are missing"""
        context = {
            "aggregated_entities": {
                "symptoms": ["headache"],
                "anatomy": [],
                "medications": [],
                "conditions": [],
                "time_expressions": []  # Missing
            },
            "follow_up_count": 0,
            "emergency_detected": False,
            "recent_messages": []
        }
        
        generator = FollowUpGenerator(context)
        
        assert generator.should_ask_followup() is True
        question = generator.generate_followup_question()
        assert question is not None
        assert "how long" in question.lower()
    
    def test_no_duration_question_when_time_expression_present(self):
        """Should not ask about duration when time expressions are present"""
        context = {
            "aggregated_entities": {
                "symptoms": ["headache"],
                "anatomy": [],
                "medications": [],
                "conditions": [],
                "time_expressions": ["2 days"]  # Present
            },
            "follow_up_count": 0,
            "emergency_detected": False,
            "recent_messages": [
                {"role": "user", "content": "I have a headache for 2 days"}
            ]
        }
        
        generator = FollowUpGenerator(context)
        
        # Should not ask about duration since we have time expression
        question = generator.generate_followup_question()
        if question:
            assert "how long" not in question.lower()


class TestFollowUpGenerationForMissingSeverity:
    """Test follow-up generation for missing severity - Requirement 5.3"""
    
    def test_asks_about_severity_when_missing(self):
        """Should ask about severity when no severity descriptors found"""
        context = {
            "aggregated_entities": {
                "symptoms": ["pain"],
                "anatomy": [],
                "medications": [],
                "conditions": [],
                "time_expressions": ["1 hour"]  # Duration present
            },
            "follow_up_count": 0,
            "emergency_detected": False,
            "recent_messages": [
                {"role": "user", "content": "I have pain for 1 hour"}
            ]
        }
        
        generator = FollowUpGenerator(context)
        
        assert generator.should_ask_followup() is True
        question = generator.generate_followup_question()
        assert question is not None
        assert "severe" in question.lower() or "scale" in question.lower()
    
    def test_no_severity_question_when_severity_present(self):
        """Should not ask about severity when severity descriptors are present"""
        context = {
            "aggregated_entities": {
                "symptoms": ["pain"],
                "anatomy": [],
                "medications": [],
                "conditions": [],
                "time_expressions": ["1 hour"]
            },
            "follow_up_count": 0,
            "emergency_detected": False,
            "recent_messages": [
                {"role": "user", "content": "I have severe pain for 1 hour"}
            ]
        }
        
        generator = FollowUpGenerator(context)
        
        # Should not ask about severity since we have severity descriptor
        question = generator.generate_followup_question()
        if question:
            # Should ask about location instead
            assert "where" in question.lower() or "other symptoms" in question.lower()


class TestFollowUpGenerationForMissingLocation:
    """Test follow-up generation for missing location - Requirement 5.4"""
    
    def test_asks_about_location_for_location_dependent_symptoms(self):
        """Should ask about location when anatomy entities missing for location-dependent symptoms"""
        context = {
            "aggregated_entities": {
                "symptoms": ["pain"],  # Location-dependent
                "anatomy": [],  # Missing
                "medications": [],
                "conditions": [],
                "time_expressions": ["2 hours"]
            },
            "follow_up_count": 0,
            "emergency_detected": False,
            "recent_messages": [
                {"role": "user", "content": "I have severe pain for 2 hours"}
            ]
        }
        
        generator = FollowUpGenerator(context)
        
        assert generator.should_ask_followup() is True
        question = generator.generate_followup_question()
        assert question is not None
        assert "where" in question.lower()
    
    def test_no_location_question_when_anatomy_present(self):
        """Should not ask about location when anatomy entities are present"""
        context = {
            "aggregated_entities": {
                "symptoms": ["pain"],
                "anatomy": ["chest"],  # Present
                "medications": [],
                "conditions": [],
                "time_expressions": ["2 hours"]
            },
            "follow_up_count": 0,
            "emergency_detected": False,
            "recent_messages": [
                {"role": "user", "content": "I have severe chest pain for 2 hours"}
            ]
        }
        
        generator = FollowUpGenerator(context)
        
        # Should not ask about location since we have anatomy
        question = generator.generate_followup_question()
        if question:
            assert "where" not in question.lower()
    
    def test_no_location_question_for_non_location_dependent_symptoms(self):
        """Should not ask about location for symptoms that don't need location"""
        context = {
            "aggregated_entities": {
                "symptoms": ["fever"],  # Not location-dependent
                "anatomy": [],
                "medications": [],
                "conditions": [],
                "time_expressions": ["1 day"]
            },
            "follow_up_count": 0,
            "emergency_detected": False,
            "recent_messages": [
                {"role": "user", "content": "I have a fever for 1 day"}
            ]
        }
        
        generator = FollowUpGenerator(context)
        
        # Should not ask about location for fever
        question = generator.generate_followup_question()
        if question:
            assert "where" not in question.lower()


class TestFollowUpGenerationForAssociatedSymptoms:
    """Test follow-up generation for associated symptoms - Requirement 5.5"""
    
    def test_asks_about_associated_symptoms_when_only_one_symptom(self):
        """Should ask about associated symptoms if only one symptom mentioned"""
        context = {
            "aggregated_entities": {
                "symptoms": ["headache"],  # Only one
                "anatomy": ["head"],
                "medications": [],
                "conditions": [],
                "time_expressions": ["3 days"]
            },
            "follow_up_count": 0,
            "emergency_detected": False,
            "recent_messages": [
                {"role": "user", "content": "I have a severe headache for 3 days"}
            ]
        }
        
        generator = FollowUpGenerator(context)
        
        assert generator.should_ask_followup() is True
        question = generator.generate_followup_question()
        assert question is not None
        assert "other symptoms" in question.lower()
    
    def test_no_associated_symptoms_question_when_multiple_symptoms(self):
        """Should not ask about associated symptoms when multiple symptoms present"""
        context = {
            "aggregated_entities": {
                "symptoms": ["headache", "fever", "nausea"],  # Multiple
                "anatomy": ["head"],
                "medications": [],
                "conditions": [],
                "time_expressions": ["3 days"]
            },
            "follow_up_count": 0,
            "emergency_detected": False,
            "recent_messages": [
                {"role": "user", "content": "I have a headache, fever, and nausea for 3 days"}
            ]
        }
        
        generator = FollowUpGenerator(context)
        
        # Should not ask about associated symptoms
        question = generator.generate_followup_question()
        if question:
            assert "other symptoms" not in question.lower()


class TestFollowUpCountLimit:
    """Test 3-question limit enforcement - Requirement 5.6"""
    
    def test_no_followup_when_count_reaches_max(self):
        """Should not ask follow-up when count reaches maximum (3)"""
        context = {
            "aggregated_entities": {
                "symptoms": ["headache"],
                "anatomy": [],
                "medications": [],
                "conditions": [],
                "time_expressions": []  # Missing info
            },
            "follow_up_count": 3,  # At maximum
            "emergency_detected": False,
            "recent_messages": []
        }
        
        generator = FollowUpGenerator(context)
        
        assert generator.should_ask_followup() is False
        question = generator.generate_followup_question()
        assert question is None
    
    def test_followup_allowed_when_count_below_max(self):
        """Should ask follow-up when count is below maximum"""
        for count in [0, 1, 2]:
            context = {
                "aggregated_entities": {
                    "symptoms": ["headache"],
                    "anatomy": [],
                    "medications": [],
                    "conditions": [],
                    "time_expressions": []
                },
                "follow_up_count": count,
                "emergency_detected": False,
                "recent_messages": []
            }
            
            generator = FollowUpGenerator(context)
            
            assert generator.should_ask_followup() is True
            question = generator.generate_followup_question()
            assert question is not None
    
    def test_ready_for_triage_when_max_followups_reached(self):
        """Should be ready for triage when max follow-ups reached, even if info incomplete"""
        context = {
            "aggregated_entities": {
                "symptoms": ["headache"],
                "anatomy": [],
                "medications": [],
                "conditions": [],
                "time_expressions": []  # Missing info
            },
            "follow_up_count": 3,  # At maximum
            "emergency_detected": False,
            "recent_messages": []
        }
        
        generator = FollowUpGenerator(context)
        
        assert generator.is_ready_for_triage() is True


class TestEmergencyHandling:
    """Test that follow-ups are skipped during emergencies"""
    
    def test_no_followup_during_emergency(self):
        """Should not ask follow-up questions when emergency detected"""
        context = {
            "aggregated_entities": {
                "symptoms": ["chest pain"],
                "anatomy": [],
                "medications": [],
                "conditions": [],
                "time_expressions": []  # Missing info
            },
            "follow_up_count": 0,
            "emergency_detected": True,  # Emergency!
            "recent_messages": []
        }
        
        generator = FollowUpGenerator(context)
        
        assert generator.should_ask_followup() is False
        question = generator.generate_followup_question()
        assert question is None


class TestReadyForTriage:
    """Test triage readiness determination - Requirement 5.7"""
    
    def test_not_ready_without_symptoms(self):
        """Should not be ready for triage without any symptoms"""
        context = {
            "aggregated_entities": {
                "symptoms": [],  # No symptoms
                "anatomy": [],
                "medications": [],
                "conditions": [],
                "time_expressions": ["1 day"]
            },
            "follow_up_count": 0,
            "emergency_detected": False,
            "recent_messages": []
        }
        
        generator = FollowUpGenerator(context)
        
        assert generator.is_ready_for_triage() is False
    
    def test_ready_with_complete_information(self):
        """Should be ready for triage with complete information"""
        context = {
            "aggregated_entities": {
                "symptoms": ["headache"],
                "anatomy": ["head"],
                "medications": [],
                "conditions": [],
                "time_expressions": ["2 days"]
            },
            "follow_up_count": 0,
            "emergency_detected": False,
            "recent_messages": [
                {"role": "user", "content": "I have a severe headache in my head for 2 days"}
            ]
        }
        
        generator = FollowUpGenerator(context)
        
        assert generator.is_ready_for_triage() is True
    
    def test_ready_with_duration_and_severity(self):
        """Should be ready for triage with duration and severity"""
        context = {
            "aggregated_entities": {
                "symptoms": ["fever"],
                "anatomy": [],
                "medications": [],
                "conditions": [],
                "time_expressions": ["3 days"]
            },
            "follow_up_count": 0,
            "emergency_detected": False,
            "recent_messages": [
                {"role": "user", "content": "I have a severe fever for 3 days"}
            ]
        }
        
        generator = FollowUpGenerator(context)
        
        assert generator.is_ready_for_triage() is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
