"""
Entity Extraction for Knowledge Ingestion Pipeline
Hybrid approach using spaCy NER + LLM-based extraction
"""

import re
import json
import logging
import requests
from typing import List, Dict, Optional, Tuple, Set
from dataclasses import dataclass, field
from collections import defaultdict

from knowledge.config import get_config

logger = logging.getLogger(__name__)


@dataclass
class ExtractedEntity:
    """Represents an extracted entity"""
    name: str
    entity_type: str
    canonical_name: str = None
    description: str = None
    confidence: float = 1.0
    source: str = "unknown"  # spacy, llm, pattern
    mentions: List[str] = field(default_factory=list)
    properties: Dict = field(default_factory=dict)

    def __post_init__(self):
        if self.canonical_name is None:
            self.canonical_name = self.name.lower().strip()


@dataclass
class ExtractedRelationship:
    """Represents an extracted relationship between entities"""
    source_entity: str  # canonical name
    relationship_type: str
    target_entity: str  # canonical name
    confidence: float = 1.0
    source: str = "unknown"
    properties: Dict = field(default_factory=dict)


@dataclass
class ExtractionResult:
    """Result of entity extraction"""
    entities: List[ExtractedEntity]
    relationships: List[ExtractedRelationship]
    metadata: Dict = field(default_factory=dict)


class SpacyExtractor:
    """Entity extraction using spaCy NER"""

    # Map spaCy entity types to our schema
    ENTITY_TYPE_MAP = {
        'PERSON': 'person',
        'ORG': 'organization',
        'GPE': 'location',
        'LOC': 'location',
        'DATE': 'date',
        'TIME': 'time',
        'MONEY': 'money',
        'PERCENT': 'percentage',
        'PRODUCT': 'product',
        'EVENT': 'event',
        'WORK_OF_ART': 'work',
        'LAW': 'law',
        'LANGUAGE': 'language',
        'NORP': 'group',  # nationalities, religious, political groups
        'FAC': 'facility',
        'QUANTITY': 'quantity',
        'ORDINAL': 'ordinal',
        'CARDINAL': 'number',
    }

    def __init__(self, model: str = None):
        config = get_config()
        self.model_name = model or config.extraction.spacy_model
        self._nlp = None

    @property
    def nlp(self):
        """Lazy load spaCy model"""
        if self._nlp is None:
            try:
                import spacy
                self._nlp = spacy.load(self.model_name)
                logger.info(f"Loaded spaCy model: {self.model_name}")
            except OSError:
                logger.warning(f"spaCy model {self.model_name} not found, downloading...")
                import spacy.cli
                spacy.cli.download(self.model_name)
                import spacy
                self._nlp = spacy.load(self.model_name)
        return self._nlp

    def extract(self, text: str) -> List[ExtractedEntity]:
        """Extract entities from text using spaCy"""
        try:
            doc = self.nlp(text)
            entities = defaultdict(lambda: {'mentions': [], 'type': None})

            for ent in doc.ents:
                canonical = ent.text.lower().strip()
                entity_type = self.ENTITY_TYPE_MAP.get(ent.label_, 'other')

                entities[canonical]['mentions'].append(ent.text)
                entities[canonical]['type'] = entity_type
                entities[canonical]['label'] = ent.label_

            results = []
            for canonical, data in entities.items():
                # Use most common mention form as name
                mention_counts = defaultdict(int)
                for m in data['mentions']:
                    mention_counts[m] += 1
                name = max(mention_counts, key=mention_counts.get)

                results.append(ExtractedEntity(
                    name=name,
                    entity_type=data['type'],
                    canonical_name=canonical,
                    confidence=0.8,  # spaCy confidence
                    source='spacy',
                    mentions=list(set(data['mentions'])),
                    properties={'spacy_label': data['label']},
                ))

            return results

        except Exception as e:
            logger.error(f"spaCy extraction error: {e}")
            return []


class LLMExtractor:
    """Entity and relationship extraction using Ollama LLM"""

    EXTRACTION_PROMPT = """Extract entities and relationships from the following text.

For entities, identify:
- People, organizations, locations
- Products, technologies, concepts
- Events, dates, quantities

For relationships, identify how entities are connected.

Return your response as JSON with this structure:
{
    "entities": [
        {
            "name": "Entity Name",
            "type": "person|organization|location|product|concept|event|other",
            "description": "Brief description if apparent"
        }
    ],
    "relationships": [
        {
            "source": "Entity Name 1",
            "relationship": "works_for|located_in|part_of|created|related_to|etc",
            "target": "Entity Name 2"
        }
    ]
}

Text to analyze:
{text}

JSON Response:"""

    def __init__(self, model: str = None, base_url: str = None):
        config = get_config()
        self.model = model or config.extraction.llm_model
        self.base_url = base_url or config.ollama.base_url
        self.timeout = config.ollama.timeout

    def extract(self, text: str, max_length: int = 4000) -> Tuple[List[ExtractedEntity], List[ExtractedRelationship]]:
        """Extract entities and relationships using LLM"""
        # Truncate text if too long
        if len(text) > max_length:
            text = text[:max_length] + "..."

        prompt = self.EXTRACTION_PROMPT.format(text=text)

        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json",
                },
                timeout=self.timeout
            )
            response.raise_for_status()

            result = response.json()
            response_text = result.get('response', '{}')

            # Parse JSON response
            try:
                data = json.loads(response_text)
            except json.JSONDecodeError:
                # Try to extract JSON from response
                json_match = re.search(r'\{[\s\S]*\}', response_text)
                if json_match:
                    data = json.loads(json_match.group())
                else:
                    logger.warning("Could not parse LLM response as JSON")
                    return [], []

            # Convert to our data structures
            entities = []
            for ent in data.get('entities', []):
                entities.append(ExtractedEntity(
                    name=ent.get('name', ''),
                    entity_type=ent.get('type', 'other'),
                    description=ent.get('description'),
                    confidence=0.7,  # LLM confidence
                    source='llm',
                ))

            relationships = []
            for rel in data.get('relationships', []):
                relationships.append(ExtractedRelationship(
                    source_entity=rel.get('source', '').lower().strip(),
                    relationship_type=rel.get('relationship', 'related_to'),
                    target_entity=rel.get('target', '').lower().strip(),
                    confidence=0.7,
                    source='llm',
                ))

            return entities, relationships

        except requests.exceptions.RequestException as e:
            logger.error(f"LLM extraction request error: {e}")
            return [], []
        except Exception as e:
            logger.error(f"LLM extraction error: {e}")
            return [], []


class PatternExtractor:
    """Pattern-based entity extraction for specific formats"""

    def __init__(self):
        self.patterns = {
            'email': (
                r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
                'email'
            ),
            'url': (
                r'https?://(?:www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b[-a-zA-Z0-9()@:%_\+.~#?&//=]*',
                'url'
            ),
            'phone': (
                r'\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b',
                'phone'
            ),
            'ip_address': (
                r'\b(?:\d{1,3}\.){3}\d{1,3}\b',
                'ip_address'
            ),
            'version': (
                r'\bv?\d+\.\d+(?:\.\d+)?(?:-[a-zA-Z0-9]+)?\b',
                'version'
            ),
            'hashtag': (
                r'#[A-Za-z][A-Za-z0-9_]*',
                'hashtag'
            ),
            'mention': (
                r'@[A-Za-z][A-Za-z0-9_]*',
                'mention'
            ),
        }

    def extract(self, text: str) -> List[ExtractedEntity]:
        """Extract entities using regex patterns"""
        entities = []

        for pattern_name, (pattern, entity_type) in self.patterns.items():
            matches = re.findall(pattern, text)
            seen = set()

            for match in matches:
                if match not in seen:
                    seen.add(match)
                    entities.append(ExtractedEntity(
                        name=match,
                        entity_type=entity_type,
                        confidence=1.0,  # Pattern match is certain
                        source='pattern',
                        mentions=[match],
                    ))

        return entities


class EntityExtractor:
    """Main entity extractor combining multiple strategies"""

    def __init__(
        self,
        use_spacy: bool = None,
        use_llm: bool = None,
        use_patterns: bool = True,
        confidence_threshold: float = None,
    ):
        config = get_config()
        self.use_spacy = use_spacy if use_spacy is not None else config.extraction.use_spacy
        self.use_llm = use_llm if use_llm is not None else config.extraction.use_llm
        self.use_patterns = use_patterns
        self.confidence_threshold = confidence_threshold or config.extraction.confidence_threshold

        # Initialize extractors lazily
        self._spacy_extractor = None
        self._llm_extractor = None
        self._pattern_extractor = None

    @property
    def spacy_extractor(self):
        if self._spacy_extractor is None:
            self._spacy_extractor = SpacyExtractor()
        return self._spacy_extractor

    @property
    def llm_extractor(self):
        if self._llm_extractor is None:
            self._llm_extractor = LLMExtractor()
        return self._llm_extractor

    @property
    def pattern_extractor(self):
        if self._pattern_extractor is None:
            self._pattern_extractor = PatternExtractor()
        return self._pattern_extractor

    def extract(self, text: str) -> ExtractionResult:
        """
        Extract entities and relationships from text.
        Combines results from multiple extractors.
        """
        all_entities: Dict[str, ExtractedEntity] = {}
        all_relationships: List[ExtractedRelationship] = []

        # Pattern extraction (fast, high precision)
        if self.use_patterns:
            for entity in self.pattern_extractor.extract(text):
                self._merge_entity(all_entities, entity)

        # spaCy extraction (good for named entities)
        if self.use_spacy:
            try:
                for entity in self.spacy_extractor.extract(text):
                    self._merge_entity(all_entities, entity)
            except Exception as e:
                logger.warning(f"spaCy extraction failed: {e}")

        # LLM extraction (best for relationships and context)
        if self.use_llm:
            try:
                entities, relationships = self.llm_extractor.extract(text)
                for entity in entities:
                    self._merge_entity(all_entities, entity)
                all_relationships.extend(relationships)
            except Exception as e:
                logger.warning(f"LLM extraction failed: {e}")

        # Filter by confidence threshold
        filtered_entities = [
            e for e in all_entities.values()
            if e.confidence >= self.confidence_threshold
        ]

        # Filter relationships to only include known entities
        entity_names = {e.canonical_name for e in filtered_entities}
        filtered_relationships = [
            r for r in all_relationships
            if r.source_entity in entity_names and r.target_entity in entity_names
        ]

        return ExtractionResult(
            entities=filtered_entities,
            relationships=filtered_relationships,
            metadata={
                'extractors_used': self._get_extractors_used(),
                'entity_count': len(filtered_entities),
                'relationship_count': len(filtered_relationships),
            }
        )

    def _merge_entity(self, entities: Dict[str, ExtractedEntity], new_entity: ExtractedEntity):
        """Merge entity with existing or add new"""
        key = new_entity.canonical_name

        if key in entities:
            existing = entities[key]
            # Combine mentions
            existing.mentions.extend(new_entity.mentions)
            existing.mentions = list(set(existing.mentions))
            # Update confidence (take higher)
            existing.confidence = max(existing.confidence, new_entity.confidence)
            # Merge properties
            existing.properties.update(new_entity.properties)
            # Update source if from more reliable extractor
            source_priority = {'pattern': 3, 'spacy': 2, 'llm': 1}
            if source_priority.get(new_entity.source, 0) > source_priority.get(existing.source, 0):
                existing.source = new_entity.source
            # Use description if not set
            if new_entity.description and not existing.description:
                existing.description = new_entity.description
        else:
            entities[key] = new_entity

    def _get_extractors_used(self) -> List[str]:
        """Get list of extractors that were used"""
        used = []
        if self.use_patterns:
            used.append('pattern')
        if self.use_spacy:
            used.append('spacy')
        if self.use_llm:
            used.append('llm')
        return used

    def extract_from_chunks(
        self,
        chunks: List[Dict],
        content_key: str = 'content',
    ) -> Tuple[List[ExtractedEntity], List[ExtractedRelationship], Dict[str, List[str]]]:
        """
        Extract entities from multiple chunks.
        Returns entities, relationships, and entity-to-chunk mapping.
        """
        all_entities: Dict[str, ExtractedEntity] = {}
        all_relationships: List[ExtractedRelationship] = []
        entity_chunk_map: Dict[str, List[str]] = defaultdict(list)

        for chunk in chunks:
            chunk_id = chunk.get('id') or str(chunk.get('chunk_index', 0))
            text = chunk[content_key]

            result = self.extract(text)

            for entity in result.entities:
                self._merge_entity(all_entities, entity)
                entity_chunk_map[entity.canonical_name].append(chunk_id)

            all_relationships.extend(result.relationships)

        # Deduplicate relationships
        seen_rels = set()
        unique_relationships = []
        for rel in all_relationships:
            key = (rel.source_entity, rel.relationship_type, rel.target_entity)
            if key not in seen_rels:
                seen_rels.add(key)
                unique_relationships.append(rel)

        return list(all_entities.values()), unique_relationships, dict(entity_chunk_map)


def entities_to_dicts(entities: List[ExtractedEntity]) -> List[Dict]:
    """Convert ExtractedEntity objects to dictionaries"""
    return [
        {
            'name': e.name,
            'entity_type': e.entity_type,
            'canonical_name': e.canonical_name,
            'description': e.description,
            'confidence': e.confidence,
            'extraction_method': e.source,
            'properties': e.properties,
        }
        for e in entities
    ]


def relationships_to_dicts(relationships: List[ExtractedRelationship]) -> List[Dict]:
    """Convert ExtractedRelationship objects to dictionaries"""
    return [
        {
            'source_entity': r.source_entity,
            'relationship_type': r.relationship_type,
            'target_entity': r.target_entity,
            'confidence': r.confidence,
            'extraction_method': r.source,
            'properties': r.properties,
        }
        for r in relationships
    ]
