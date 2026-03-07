"""
Unit tests for Medical NER Client
Tests entity extraction, type mapping, graceful degradation, and text truncation
"""

import pytest
import sys
from unittest.mock import Mock, patch, MagicMock

# Mock spacy module before importing medical_ner
sys.modules['spacy'] = Mock()
sys.modules['spacy.language'] = Mock()

from backend.integrations.medical_ner import MedicalNERClient, MedicalEntity


class TestMedicalEntity:
    """Test MedicalEntity class"""
    
    def test_medical_entity_creation(self):
        """Test creating a MedicalEntity"""
        entity = MedicalEntity(
            entity_type="SYMPTOM",
            text="headache",
            score=0.95,
            category="SYMPTOM"
        )
        
        assert entity.type == "SYMPTOM"
        assert entity.text == "headache"
        assert entity.score == 0.95
        assert entity.category == "SYMPTOM"
    
    def test_medical_entity_to_dict(self):
        """Test converting MedicalEntity to dictionary"""
        entity = MedicalEntity(
            entity_type="MEDICAL_CONDITION",
            text="diabetes",
            score=0.92,
            category="DISEASE"
        )
        
        entity_dict = entity.to_dict()
        
        assert entity_dict["type"] == "MEDICAL_CONDITION"
        assert entity_dict["text"] == "diabetes"
        assert entity_dict["score"] == 0.92
        assert entity_dict["category"] == "DISEASE"


class TestMedicalNERClient:
    """Test MedicalNERClient class"""
    
    @pytest.fixture
    def mock_spacy_model(self):
        """Create a mock spaCy model"""
        mock_model = Mock()
        mock_doc = Mock()
        mock_model.return_value = mock_doc
        return mock_model, mock_doc
    
    def test_client_initialization_success(self):
        """Test successful client initialization with available model"""
        with patch('backend.integrations.medical_ner.spacy.load') as mock_load:
            mock_load.return_value = Mock()
            
            client = MedicalNERClient(model_name="en_core_sci_md")
            
            assert client.is_available() is True
            assert client.nlp is not None
            mock_load.assert_called_once_with("en_core_sci_md")
    
    def test_client_initialization_model_not_found(self):
        """Test client initialization when model is not found"""
        with patch('backend.integrations.medical_ner.spacy.load') as mock_load:
            mock_load.side_effect = OSError("Model not found")
            
            client = MedicalNERClient(model_name="nonexistent_model")
            
            assert client.is_available() is False
            assert client.nlp is None
    
    def test_client_initialization_unexpected_error(self):
        """Test client initialization with unexpected error"""
        with patch('backend.integrations.medical_ner.spacy.load') as mock_load:
            mock_load.side_effect = Exception("Unexpected error")
            
            client = MedicalNERClient()
            
            assert client.is_available() is False
            assert client.nlp is None
    
    def test_extract_entities_with_sample_medical_text(self):
        """Test entity extraction with sample medical text"""
        with patch('backend.integrations.medical_ner.spacy.load') as mock_load:
            # Create mock entities
            mock_ent1 = Mock()
            mock_ent1.text = "headache"
            mock_ent1.label_ = "SYMPTOM"
            
            mock_ent2 = Mock()
            mock_ent2.text = "head"
            mock_ent2.label_ = "ANATOMY"
            
            mock_ent3 = Mock()
            mock_ent3.text = "2 days"
            mock_ent3.label_ = "TIME"
            
            # Create mock doc
            mock_doc = Mock()
            mock_doc.ents = [mock_ent1, mock_ent2, mock_ent3]
            
            # Create mock model
            mock_model = Mock()
            mock_model.return_value = mock_doc
            mock_load.return_value = mock_model
            
            client = MedicalNERClient()
            entities = client.extract_entities("I have a headache in my head for 2 days")
            
            assert len(entities) == 3
            assert entities[0].type == "SYMPTOM"
            assert entities[0].text == "headache"
            assert entities[1].type == "ANATOMY"
            assert entities[1].text == "head"
            assert entities[2].type == "TIME_EXPRESSION"
            assert entities[2].text == "2 days"
    
    def test_extract_entities_empty_text(self):
        """Test entity extraction with empty text"""
        with patch('backend.integrations.medical_ner.spacy.load') as mock_load:
            mock_load.return_value = Mock()
            
            client = MedicalNERClient()
            entities = client.extract_entities("")
            
            assert len(entities) == 0
    
    def test_extract_entities_whitespace_only(self):
        """Test entity extraction with whitespace-only text"""
        with patch('backend.integrations.medical_ner.spacy.load') as mock_load:
            mock_load.return_value = Mock()
            
            client = MedicalNERClient()
            entities = client.extract_entities("   \n\t  ")
            
            assert len(entities) == 0
    
    def test_extract_entities_model_unavailable(self):
        """Test graceful degradation when model is unavailable"""
        with patch('backend.integrations.medical_ner.spacy.load') as mock_load:
            mock_load.side_effect = OSError("Model not found")
            
            client = MedicalNERClient()
            entities = client.extract_entities("I have a headache")
            
            assert len(entities) == 0
            assert client.is_available() is False
    
    def test_extract_entities_processing_error(self):
        """Test graceful degradation when processing fails"""
        with patch('backend.integrations.medical_ner.spacy.load') as mock_load:
            mock_model = Mock()
            mock_model.side_effect = Exception("Processing error")
            mock_load.return_value = mock_model
            
            client = MedicalNERClient()
            entities = client.extract_entities("I have a headache")
            
            assert len(entities) == 0
    
    def test_text_truncation_for_long_messages(self):
        """Test text truncation for messages exceeding max length"""
        with patch('backend.integrations.medical_ner.spacy.load') as mock_load:
            # Create mock doc with no entities
            mock_doc = Mock()
            mock_doc.ents = []
            
            # Create mock model that tracks the text it receives
            mock_model = Mock()
            mock_model.return_value = mock_doc
            mock_load.return_value = mock_model
            
            client = MedicalNERClient()
            
            # Create text longer than MAX_TEXT_LENGTH (5000 chars)
            long_text = "a" * 6000
            entities = client.extract_entities(long_text)
            
            # Verify the model was called with truncated text
            mock_model.assert_called_once()
            processed_text = mock_model.call_args[0][0]
            assert len(processed_text) == MedicalNERClient.MAX_TEXT_LENGTH
            assert len(processed_text) == 5000
    
    def test_entity_type_mapping_disease_to_condition(self):
        """Test entity type mapping from DISEASE to MEDICAL_CONDITION"""
        with patch('backend.integrations.medical_ner.spacy.load') as mock_load:
            mock_ent = Mock()
            mock_ent.text = "diabetes"
            mock_ent.label_ = "DISEASE"
            
            mock_doc = Mock()
            mock_doc.ents = [mock_ent]
            
            mock_model = Mock()
            mock_model.return_value = mock_doc
            mock_load.return_value = mock_model
            
            client = MedicalNERClient()
            entities = client.extract_entities("I have diabetes")
            
            assert len(entities) == 1
            assert entities[0].type == "MEDICAL_CONDITION"
            assert entities[0].category == "DISEASE"
    
    def test_entity_type_mapping_chemical_to_medication(self):
        """Test entity type mapping from CHEMICAL to MEDICATION"""
        with patch('backend.integrations.medical_ner.spacy.load') as mock_load:
            mock_ent = Mock()
            mock_ent.text = "aspirin"
            mock_ent.label_ = "CHEMICAL"
            
            mock_doc = Mock()
            mock_doc.ents = [mock_ent]
            
            mock_model = Mock()
            mock_model.return_value = mock_doc
            mock_load.return_value = mock_model
            
            client = MedicalNERClient()
            entities = client.extract_entities("I take aspirin")
            
            assert len(entities) == 1
            assert entities[0].type == "MEDICATION"
            assert entities[0].category == "CHEMICAL"
    
    def test_entity_type_mapping_drug_to_medication(self):
        """Test entity type mapping from DRUG to MEDICATION"""
        with patch('backend.integrations.medical_ner.spacy.load') as mock_load:
            mock_ent = Mock()
            mock_ent.text = "ibuprofen"
            mock_ent.label_ = "DRUG"
            
            mock_doc = Mock()
            mock_doc.ents = [mock_ent]
            
            mock_model = Mock()
            mock_model.return_value = mock_doc
            mock_load.return_value = mock_model
            
            client = MedicalNERClient()
            entities = client.extract_entities("I take ibuprofen")
            
            assert len(entities) == 1
            assert entities[0].type == "MEDICATION"
    
    def test_entity_type_mapping_body_part_to_anatomy(self):
        """Test entity type mapping from BODY_PART to ANATOMY"""
        with patch('backend.integrations.medical_ner.spacy.load') as mock_load:
            mock_ent = Mock()
            mock_ent.text = "chest"
            mock_ent.label_ = "BODY_PART"
            
            mock_doc = Mock()
            mock_doc.ents = [mock_ent]
            
            mock_model = Mock()
            mock_model.return_value = mock_doc
            mock_load.return_value = mock_model
            
            client = MedicalNERClient()
            entities = client.extract_entities("My chest hurts")
            
            assert len(entities) == 1
            assert entities[0].type == "ANATOMY"
    
    def test_entity_type_mapping_case_insensitive(self):
        """Test entity type mapping is case-insensitive"""
        with patch('backend.integrations.medical_ner.spacy.load') as mock_load:
            mock_ent = Mock()
            mock_ent.text = "fever"
            mock_ent.label_ = "symptom"  # lowercase
            
            mock_doc = Mock()
            mock_doc.ents = [mock_ent]
            
            mock_model = Mock()
            mock_model.return_value = mock_doc
            mock_load.return_value = mock_model
            
            client = MedicalNERClient()
            entities = client.extract_entities("I have a fever")
            
            assert len(entities) == 1
            assert entities[0].type == "SYMPTOM"
    
    def test_unmapped_entity_types_are_skipped(self):
        """Test that unmapped entity types are skipped"""
        with patch('backend.integrations.medical_ner.spacy.load') as mock_load:
            mock_ent1 = Mock()
            mock_ent1.text = "headache"
            mock_ent1.label_ = "SYMPTOM"
            
            mock_ent2 = Mock()
            mock_ent2.text = "something"
            mock_ent2.label_ = "UNKNOWN_TYPE"  # Not in mapping
            
            mock_doc = Mock()
            mock_doc.ents = [mock_ent1, mock_ent2]
            
            mock_model = Mock()
            mock_model.return_value = mock_doc
            mock_load.return_value = mock_model
            
            client = MedicalNERClient()
            entities = client.extract_entities("I have a headache and something")
            
            # Only the mapped entity should be returned
            assert len(entities) == 1
            assert entities[0].type == "SYMPTOM"
            assert entities[0].text == "headache"
    
    def test_default_confidence_score(self):
        """Test that entities have default confidence score of 0.95"""
        with patch('backend.integrations.medical_ner.spacy.load') as mock_load:
            mock_ent = Mock()
            mock_ent.text = "fever"
            mock_ent.label_ = "SYMPTOM"
            
            mock_doc = Mock()
            mock_doc.ents = [mock_ent]
            
            mock_model = Mock()
            mock_model.return_value = mock_doc
            mock_load.return_value = mock_model
            
            client = MedicalNERClient()
            entities = client.extract_entities("I have a fever")
            
            assert len(entities) == 1
            assert entities[0].score == 0.95
    
    def test_multiple_entities_extraction(self):
        """Test extraction of multiple entities from complex text"""
        with patch('backend.integrations.medical_ner.spacy.load') as mock_load:
            mock_ent1 = Mock()
            mock_ent1.text = "chest pain"
            mock_ent1.label_ = "SYMPTOM"
            
            mock_ent2 = Mock()
            mock_ent2.text = "chest"
            mock_ent2.label_ = "ANATOMY"
            
            mock_ent3 = Mock()
            mock_ent3.text = "aspirin"
            mock_ent3.label_ = "CHEMICAL"
            
            mock_ent4 = Mock()
            mock_ent4.text = "3 hours"
            mock_ent4.label_ = "TIME"
            
            mock_doc = Mock()
            mock_doc.ents = [mock_ent1, mock_ent2, mock_ent3, mock_ent4]
            
            mock_model = Mock()
            mock_model.return_value = mock_doc
            mock_load.return_value = mock_model
            
            client = MedicalNERClient()
            entities = client.extract_entities(
                "I have chest pain in my chest, took aspirin 3 hours ago"
            )
            
            assert len(entities) == 4
            assert entities[0].type == "SYMPTOM"
            assert entities[1].type == "ANATOMY"
            assert entities[2].type == "MEDICATION"
            assert entities[3].type == "TIME_EXPRESSION"
    
    def test_map_entity_type_direct_mapping(self):
        """Test _map_entity_type with direct mapping"""
        with patch('backend.integrations.medical_ner.spacy.load') as mock_load:
            mock_load.return_value = Mock()
            client = MedicalNERClient()
            
            assert client._map_entity_type("SYMPTOM") == "SYMPTOM"
            assert client._map_entity_type("DISEASE") == "MEDICAL_CONDITION"
            assert client._map_entity_type("CHEMICAL") == "MEDICATION"
            assert client._map_entity_type("ANATOMY") == "ANATOMY"
            assert client._map_entity_type("TIME") == "TIME_EXPRESSION"
    
    def test_map_entity_type_no_mapping(self):
        """Test _map_entity_type returns None for unmapped types"""
        with patch('backend.integrations.medical_ner.spacy.load') as mock_load:
            mock_load.return_value = Mock()
            client = MedicalNERClient()
            
            assert client._map_entity_type("UNKNOWN") is None
            assert client._map_entity_type("RANDOM_TYPE") is None
    
    def test_original_spacy_label_stored_as_category(self):
        """Test that original spaCy label is stored as category"""
        with patch('backend.integrations.medical_ner.spacy.load') as mock_load:
            mock_ent = Mock()
            mock_ent.text = "diabetes"
            mock_ent.label_ = "DISEASE"
            
            mock_doc = Mock()
            mock_doc.ents = [mock_ent]
            
            mock_model = Mock()
            mock_model.return_value = mock_doc
            mock_load.return_value = mock_model
            
            client = MedicalNERClient()
            entities = client.extract_entities("I have diabetes")
            
            assert len(entities) == 1
            assert entities[0].type == "MEDICAL_CONDITION"
            assert entities[0].category == "DISEASE"  # Original label preserved


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
