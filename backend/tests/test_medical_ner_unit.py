"""
Unit tests for Medical NER Client
Tests entity extraction, type mapping, graceful degradation, and text truncation
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from backend.integrations.medical_ner import MedicalNERClient, MedicalEntity


class TestMedicalEntity:
    """Test MedicalEntity data class"""
    
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
            entity_type="MEDICATION",
            text="aspirin",
            score=0.98,
            category="DRUG"
        )
        
        result = entity.to_dict()
        
        assert result == {
            "type": "MEDICATION",
            "text": "aspirin",
            "score": 0.98,
            "category": "DRUG"
        }


class TestMedicalNERClient:
    """Test MedicalNERClient functionality"""
    
    def test_client_initialization_success(self):
        """Test successful client initialization with mock model"""
        with patch('backend.integrations.medical_ner.spacy.load') as mock_load:
            mock_nlp = Mock()
            mock_load.return_value = mock_nlp
            
            client = MedicalNERClient(model_name="en_core_sci_md")
            
            assert client.is_available() is True
            assert client.nlp == mock_nlp
            mock_load.assert_called_once_with("en_core_sci_md")
    
    def test_client_initialization_model_not_found(self):
        """Test graceful degradation when model not found"""
        with patch('backend.integrations.medical_ner.spacy.load') as mock_load:
            mock_load.side_effect = OSError("Model not found")
            
            client = MedicalNERClient(model_name="en_core_sci_md")
            
            assert client.is_available() is False
            assert client.nlp is None
    
    def test_client_initialization_unexpected_error(self):
        """Test graceful degradation on unexpected error"""
        with patch('backend.integrations.medical_ner.spacy.load') as mock_load:
            mock_load.side_effect = Exception("Unexpected error")
            
            client = MedicalNERClient(model_name="en_core_sci_md")
            
            assert client.is_available() is False
            assert client.nlp is None
    
    def test_extract_entities_with_sample_medical_text(self):
        """Test entity extraction with sample medical text"""
        # Create mock spaCy entities
        mock_ent1 = Mock()
        mock_ent1.text = "headache"
        mock_ent1.label_ = "SYMPTOM"
        
        mock_ent2 = Mock()
        mock_ent2.text = "head"
        mock_ent2.label_ = "ANATOMY"
        
        mock_ent3 = Mock()
        mock_ent3.text = "aspirin"
        mock_ent3.label_ = "CHEMICAL"
        
        # Create mock doc
        mock_doc = Mock()
        mock_doc.ents = [mock_ent1, mock_ent2, mock_ent3]
        
        # Create mock nlp
        mock_nlp = Mock()
        mock_nlp.return_value = mock_doc
        
        with patch('backend.integrations.medical_ner.spacy.load') as mock_load:
            mock_load.return_value = mock_nlp
            
            client = MedicalNERClient()
            entities = client.extract_entities("I have a headache in my head and took aspirin")
            
            assert len(entities) == 3
            assert entities[0].type == "SYMPTOM"
            assert entities[0].text == "headache"
            assert entities[1].type == "ANATOMY"
            assert entities[1].text == "head"
            assert entities[2].type == "MEDICATION"
            assert entities[2].text == "aspirin"
    
    def test_entity_type_mapping_disease_to_medical_condition(self):
        """Test mapping DISEASE to MEDICAL_CONDITION"""
        mock_ent = Mock()
        mock_ent.text = "diabetes"
        mock_ent.label_ = "DISEASE"
        
        mock_doc = Mock()
        mock_doc.ents = [mock_ent]
        
        mock_nlp = Mock()
        mock_nlp.return_value = mock_doc
        
        with patch('backend.integrations.medical_ner.spacy.load') as mock_load:
            mock_load.return_value = mock_nlp
            
            client = MedicalNERClient()
            entities = client.extract_entities("Patient has diabetes")
            
            assert len(entities) == 1
            assert entities[0].type == "MEDICAL_CONDITION"
            assert entities[0].text == "diabetes"
            assert entities[0].category == "DISEASE"
    
    def test_entity_type_mapping_chemical_to_medication(self):
        """Test mapping CHEMICAL to MEDICATION"""
        mock_ent = Mock()
        mock_ent.text = "ibuprofen"
        mock_ent.label_ = "CHEMICAL"
        
        mock_doc = Mock()
        mock_doc.ents = [mock_ent]
        
        mock_nlp = Mock()
        mock_nlp.return_value = mock_doc
        
        with patch('backend.integrations.medical_ner.spacy.load') as mock_load:
            mock_load.return_value = mock_nlp
            
            client = MedicalNERClient()
            entities = client.extract_entities("Taking ibuprofen")
            
            assert len(entities) == 1
            assert entities[0].type == "MEDICATION"
    
    def test_entity_type_mapping_time_to_time_expression(self):
        """Test mapping TIME to TIME_EXPRESSION"""
        mock_ent = Mock()
        mock_ent.text = "2 days ago"
        mock_ent.label_ = "TIME"
        
        mock_doc = Mock()
        mock_doc.ents = [mock_ent]
        
        mock_nlp = Mock()
        mock_nlp.return_value = mock_doc
        
        with patch('backend.integrations.medical_ner.spacy.load') as mock_load:
            mock_load.return_value = mock_nlp
            
            client = MedicalNERClient()
            entities = client.extract_entities("Started 2 days ago")
            
            assert len(entities) == 1
            assert entities[0].type == "TIME_EXPRESSION"
    
    def test_entity_type_mapping_unmapped_label_skipped(self):
        """Test that unmapped entity labels are skipped"""
        mock_ent1 = Mock()
        mock_ent1.text = "headache"
        mock_ent1.label_ = "SYMPTOM"
        
        mock_ent2 = Mock()
        mock_ent2.text = "unknown"
        mock_ent2.label_ = "UNKNOWN_TYPE"
        
        mock_doc = Mock()
        mock_doc.ents = [mock_ent1, mock_ent2]
        
        mock_nlp = Mock()
        mock_nlp.return_value = mock_doc
        
        with patch('backend.integrations.medical_ner.spacy.load') as mock_load:
            mock_load.return_value = mock_nlp
            
            client = MedicalNERClient()
            entities = client.extract_entities("headache and unknown")
            
            # Only the mapped entity should be returned
            assert len(entities) == 1
            assert entities[0].type == "SYMPTOM"
    
    def test_graceful_degradation_when_model_unavailable(self):
        """Test graceful degradation when model is unavailable"""
        with patch('backend.integrations.medical_ner.spacy.load') as mock_load:
            mock_load.side_effect = OSError("Model not found")
            
            client = MedicalNERClient()
            entities = client.extract_entities("I have a headache")
            
            # Should return empty list, not raise exception
            assert entities == []
            assert client.is_available() is False
    
    def test_extract_entities_with_empty_text(self):
        """Test extraction with empty text"""
        with patch('backend.integrations.medical_ner.spacy.load') as mock_load:
            mock_nlp = Mock()
            mock_load.return_value = mock_nlp
            
            client = MedicalNERClient()
            entities = client.extract_entities("")
            
            assert entities == []
            # nlp should not be called for empty text
            mock_nlp.assert_not_called()
    
    def test_extract_entities_with_whitespace_only(self):
        """Test extraction with whitespace-only text"""
        with patch('backend.integrations.medical_ner.spacy.load') as mock_load:
            mock_nlp = Mock()
            mock_load.return_value = mock_nlp
            
            client = MedicalNERClient()
            entities = client.extract_entities("   \n\t  ")
            
            assert entities == []
            mock_nlp.assert_not_called()
    
    def test_text_truncation_for_long_messages(self):
        """Test text truncation for messages exceeding max length"""
        # Create a long text exceeding MAX_TEXT_LENGTH
        long_text = "headache " * 1000  # Much longer than 5000 chars
        
        mock_doc = Mock()
        mock_doc.ents = []
        
        mock_nlp = Mock()
        mock_nlp.return_value = mock_doc
        
        with patch('backend.integrations.medical_ner.spacy.load') as mock_load:
            mock_load.return_value = mock_nlp
            
            client = MedicalNERClient()
            entities = client.extract_entities(long_text)
            
            # Verify nlp was called with truncated text
            mock_nlp.assert_called_once()
            called_text = mock_nlp.call_args[0][0]
            assert len(called_text) == client.MAX_TEXT_LENGTH
    
    def test_extract_entities_handles_processing_error(self):
        """Test that processing errors are handled gracefully"""
        mock_nlp = Mock()
        mock_nlp.side_effect = Exception("Processing error")
        
        with patch('backend.integrations.medical_ner.spacy.load') as mock_load:
            mock_load.return_value = mock_nlp
            
            client = MedicalNERClient()
            entities = client.extract_entities("I have a headache")
            
            # Should return empty list, not raise exception
            assert entities == []
    
    def test_confidence_scoring_for_extracted_entities(self):
        """Test that extracted entities have confidence scores"""
        mock_ent = Mock()
        mock_ent.text = "fever"
        mock_ent.label_ = "SYMPTOM"
        
        mock_doc = Mock()
        mock_doc.ents = [mock_ent]
        
        mock_nlp = Mock()
        mock_nlp.return_value = mock_doc
        
        with patch('backend.integrations.medical_ner.spacy.load') as mock_load:
            mock_load.return_value = mock_nlp
            
            client = MedicalNERClient()
            entities = client.extract_entities("I have a fever")
            
            assert len(entities) == 1
            assert entities[0].score == 0.95  # Default confidence score
            assert 0.0 <= entities[0].score <= 1.0
    
    def test_multiple_entities_of_same_type(self):
        """Test extraction of multiple entities of the same type"""
        mock_ent1 = Mock()
        mock_ent1.text = "headache"
        mock_ent1.label_ = "SYMPTOM"
        
        mock_ent2 = Mock()
        mock_ent2.text = "fever"
        mock_ent2.label_ = "SYMPTOM"
        
        mock_ent3 = Mock()
        mock_ent3.text = "nausea"
        mock_ent3.label_ = "SYMPTOM"
        
        mock_doc = Mock()
        mock_doc.ents = [mock_ent1, mock_ent2, mock_ent3]
        
        mock_nlp = Mock()
        mock_nlp.return_value = mock_doc
        
        with patch('backend.integrations.medical_ner.spacy.load') as mock_load:
            mock_load.return_value = mock_nlp
            
            client = MedicalNERClient()
            entities = client.extract_entities("I have headache, fever, and nausea")
            
            assert len(entities) == 3
            assert all(e.type == "SYMPTOM" for e in entities)
            assert [e.text for e in entities] == ["headache", "fever", "nausea"]
    
    def test_case_insensitive_entity_mapping(self):
        """Test that entity type mapping is case-insensitive"""
        mock_ent = Mock()
        mock_ent.text = "chest pain"
        mock_ent.label_ = "symptom"  # lowercase
        
        mock_doc = Mock()
        mock_doc.ents = [mock_ent]
        
        mock_nlp = Mock()
        mock_nlp.return_value = mock_doc
        
        with patch('backend.integrations.medical_ner.spacy.load') as mock_load:
            mock_load.return_value = mock_nlp
            
            client = MedicalNERClient()
            entities = client.extract_entities("chest pain")
            
            assert len(entities) == 1
            assert entities[0].type == "SYMPTOM"
