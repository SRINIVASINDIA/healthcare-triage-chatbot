"""
Medical NER Client using open-source spaCy models
Replaces AWS Comprehend Medical for cost-effective entity extraction
"""

import logging
from typing import List, Dict, Optional
import spacy
from spacy.language import Language

logger = logging.getLogger(__name__)


class MedicalEntity:
    """Represents a medical entity extracted from text"""
    
    def __init__(self, entity_type: str, text: str, score: float, category: Optional[str] = None):
        self.type = entity_type
        self.text = text
        self.score = score
        self.category = category
    
    def to_dict(self) -> Dict:
        return {
            "type": self.type,
            "text": self.text,
            "score": self.score,
            "category": self.category
        }


class MedicalNERClient:
    """Client for extracting medical entities using spaCy with scispaCy models"""
    
    # Mapping from spaCy entity labels to system entity types
    ENTITY_TYPE_MAPPING = {
        # scispaCy labels to system types
        "DISEASE": "MEDICAL_CONDITION",
        "SYMPTOM": "SYMPTOM",
        "CHEMICAL": "MEDICATION",
        "ANATOMY": "ANATOMY",
        "TIME": "TIME_EXPRESSION",
        # Additional mappings for broader coverage
        "DRUG": "MEDICATION",
        "MEDICATION": "MEDICATION",
        "BODY_PART": "ANATOMY",
        "ORGAN": "ANATOMY",
        "CONDITION": "MEDICAL_CONDITION",
    }
    
    # Maximum text length to process (characters)
    MAX_TEXT_LENGTH = 5000
    
    def __init__(self, model_name: str = "en_core_sci_md"):
        """
        Initialize the Medical NER client with spaCy model
        
        Args:
            model_name: Name of the spaCy model to load (default: en_core_sci_md)
        """
        self.model_name = model_name
        self.nlp: Optional[Language] = None
        self._model_available = False
        
        try:
            logger.info(f"Loading spaCy model: {model_name}")
            self.nlp = spacy.load(model_name)
            self._model_available = True
            logger.info(f"Successfully loaded spaCy model: {model_name}")
        except OSError as e:
            logger.warning(f"Failed to load spaCy model {model_name}: {e}")
            logger.warning("Medical NER will operate in fallback mode (no entity extraction)")
            self._model_available = False
        except Exception as e:
            logger.error(f"Unexpected error loading spaCy model: {e}")
            self._model_available = False
    
    def is_available(self) -> bool:
        """Check if the NER model is available"""
        return self._model_available
    
    def extract_entities(self, text: str) -> List[MedicalEntity]:
        """
        Extract medical entities from text using spaCy NER pipeline
        
        Args:
            text: Input text to extract entities from
            
        Returns:
            List of MedicalEntity objects with extracted entities
        """
        # Fallback if model not available
        if not self._model_available or self.nlp is None:
            logger.warning("Medical NER model not available, returning empty entity list")
            return []
        
        # Validate input
        if not text or not text.strip():
            logger.debug("Empty text provided, returning empty entity list")
            return []
        
        # Truncate text if too long
        original_length = len(text)
        if original_length > self.MAX_TEXT_LENGTH:
            text = text[:self.MAX_TEXT_LENGTH]
            logger.warning(f"Text truncated from {original_length} to {self.MAX_TEXT_LENGTH} characters")
        
        try:
            # Process text with spaCy
            doc = self.nlp(text)
            
            # Extract entities
            entities = []
            for ent in doc.ents:
                # Map spaCy label to system entity type
                entity_type = self._map_entity_type(ent.label_)
                
                # Skip unmapped entity types
                if entity_type is None:
                    continue
                
                # Create MedicalEntity with confidence score
                # spaCy doesn't provide confidence scores by default, so we use 0.95 as a default
                entity = MedicalEntity(
                    entity_type=entity_type,
                    text=ent.text,
                    score=0.95,  # Default confidence for spaCy entities
                    category=ent.label_  # Store original spaCy label as category
                )
                entities.append(entity)
            
            logger.info(f"Extracted {len(entities)} medical entities from text")
            return entities
            
        except Exception as e:
            logger.error(f"Error extracting entities: {e}")
            return []
    
    def _map_entity_type(self, spacy_label: str) -> Optional[str]:
        """
        Map spaCy entity label to system entity type
        
        Args:
            spacy_label: Entity label from spaCy
            
        Returns:
            System entity type or None if not mapped
        """
        # Direct mapping
        if spacy_label in self.ENTITY_TYPE_MAPPING:
            return self.ENTITY_TYPE_MAPPING[spacy_label]
        
        # Case-insensitive fallback
        spacy_label_upper = spacy_label.upper()
        for key, value in self.ENTITY_TYPE_MAPPING.items():
            if key.upper() == spacy_label_upper:
                return value
        
        # No mapping found
        logger.debug(f"No mapping found for spaCy label: {spacy_label}")
        return None

