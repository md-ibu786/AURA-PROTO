# llm_entity_extractor.py
# LLM-powered entity extraction using Google Gemini for knowledge graph construction

# Extracts structured entities (Topic, Concept, Methodology, Finding) from document
# chunks using Gemini with configurable prompts, confidence scoring, and validation.
# Ported from AURA-CHAT/backend/llm_entity_extractor.py for consistency.

# @see: api/kg_processor.py - Integration point for entity extraction
# @note: Uses Vertex AI SDK via services/vertex_ai_client

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import time
from typing import Dict, List, Literal, Optional, Any, Tuple

from pydantic import BaseModel, Field

from services.vertex_ai_client import GenerationConfig, generate_content, get_model

# ============================================================================
# CONFIGURATION CONSTANTS
# ============================================================================

LLM_ENTITY_BATCH_SIZE = 3000  # Tokens per batch
LLM_ENTITY_MAX_PARALLEL = 2  # Max concurrent requests
MAX_RETRIES = 3  # Retry attempts
RETRY_BACKOFF_BASE = 2.0  # Exponential backoff base
LLM_ENTITY_TEMPERATURE = 0.2  # Generation temperature
LLM_RELATIONSHIP_MIN_CONFIDENCE = 0.3  # Minimum confidence for relationships
LLM_RELATIONSHIP_MAX_PER_DOCUMENT = 50  # Max relationships per document
LLM_RELATIONSHIP_MAX_PER_ENTITY = 10  # Max relationships per source entity
DEFAULT_EXTRACTION_MODEL = os.getenv(
    "LLM_ENTITY_EXTRACTION_MODEL",
    "gemini-2.5-flash-lite",
)

# Supported relationship types for entity-entity relationships
RELATIONSHIP_TYPES = [
    "DEFINES",
    "DEPENDS_ON",
    "USES",
    "SUPPORTS",
    "CONTRADICTS",
    "EXTENDS",
    "IMPLEMENTS",
    "REFERENCES",
    "RELATED_TO",
]

# ============================================================================
# PYDANTIC MODELS
# ============================================================================


class ExtractedEntity(BaseModel):
    """Validated entity extracted from text."""

    name: str = Field(..., min_length=1, max_length=200)
    type: Literal["Topic", "Concept", "Methodology", "Finding"]
    definition: str = Field(default="", max_length=500)
    confidence_score: float = Field(default=0.7, ge=0.0, le=1.0)
    source_text: Optional[str] = Field(default=None, max_length=200)
    category: str = Field(default="General", max_length=100)


class Relationship(BaseModel):
    """
    Represents a semantic relationship between two entities.

    Entity-entity relationships enable multi-hop graph reasoning by
    connecting concepts, topics, methodologies, and findings.
    """

    source_entity: str = Field(
        ..., min_length=1, description="Name of the source entity"
    )
    target_entity: str = Field(
        ..., min_length=1, description="Name of the target entity"
    )
    relationship_type: Literal[
        "DEFINES",
        "DEPENDS_ON",
        "USES",
        "SUPPORTS",
        "CONTRADICTS",
        "EXTENDS",
        "IMPLEMENTS",
        "REFERENCES",
        "RELATED_TO",
    ] = Field(..., description="Type of semantic relationship")
    confidence: float = Field(
        default=0.5, ge=0.0, le=1.0, description="Confidence score 0-1"
    )
    evidence: Optional[str] = Field(
        default=None, max_length=300, description="Text supporting the relationship"
    )


# ============================================================================
# EXTRACTION PROMPT
# ============================================================================

ENTITY_EXTRACTION_PROMPT = """<instruction>
You are an expert academic researcher. Extract entities from the text below into a structured JSON format.
ACCURACY IS CRITICAL. Do not hallucinate. Only extract what is explicitly stated or clearly implied.
</instruction>

<categories>
1. concepts: Specific technical terms, theories, laws, or fundamental ideas (e.g., "Nash Equilibrium").
2. topics: Broader fields of study or domains (e.g., "Game Theory").
3. methodologies: Research methods, algorithms, or techniques (e.g., "Double-Blind Study").
4. findings: Key conclusions, results, or statistics.
</categories>

<schema>
For each extracted entity, provide this exact structure:
- "name": Full canonical name. EXPAND ACRONYMS (e.g., "ML" -> "Machine Learning").
- "definition": One-sentence definition derived from the text.
- "category": The general academic discipline (e.g., "Computer Science").
- "confidence": Float 0.0-1.0.
- "context": A short excerpt (max 100 chars) showing usage.
</schema>

<example>
{{
  "concepts": [
    {{
      "name": "Graph Neural Network",
      "definition": "A class of neural networks for processing data best represented by graph data structures.",
      "category": "Computer Science",
      "confidence": 0.95,
      "context": "We utilize a Graph Neural Network to model the relationships..."
    }}
  ],
  "topics": [],
  "methodologies": [],
  "findings": []
}}
</example>

<input_text>
{text}
</input_text>"""

# ============================================================================
# LOGGING
# ============================================================================

logger = logging.getLogger(__name__)


# ============================================================================
# MAIN EXTRACTOR CLASS
# ============================================================================


class LLMEntityExtractor:
    """
    LLM-powered entity extraction using Google Gemini.

    Extracts structured entities from academic text with:
    - Batch processing for long documents
    - Retry logic with exponential backoff
    - JSON validation via Pydantic
    - Test mode for unit testing
    """

    def __init__(self, model_name: str = DEFAULT_EXTRACTION_MODEL, api_key: str = None):
        """
        Initialize with Gemini model.

        Args:
            model_name: Name of the Gemini model to use (Vertex AI model name)
            api_key: Deprecated. Vertex AI uses ADC credentials instead.
        """
        self.model_name = model_name
        self._test_mode = os.getenv("AURA_TEST_MODE", "").lower() == "true"
        self._model = None
        self._encoding = None

        # Initialize tiktoken for token counting
        try:
            import tiktoken

            self._encoding = tiktoken.get_encoding("cl100k_base")
        except ImportError:
            logger.warning("tiktoken not available, using whitespace tokenization")

        if api_key:
            logger.warning("LLMEntityExtractor no longer uses API keys; ignoring api_key")

        if not self._test_mode:
            self._initialize_model()
        else:
            logger.info("LLMEntityExtractor initialized in test mode")

    def _initialize_model(self):
        """Initialize the Gemini model."""
        try:
            self._model = get_model(self.model_name)
            logger.info(f"Initialized LLMEntityExtractor with model: {self.model_name}")
        except Exception as e:
            logger.error(f"Failed to initialize Vertex AI model: {e}")

    def _count_tokens(self, text: str) -> int:
        """Count tokens in text."""
        if self._encoding:
            return len(self._encoding.encode(text))
        return len(text.split())

    async def extract_entities(
        self, text: str, doc_id: str = "unknown", entity_types: List[str] = None
    ) -> Dict[str, List[ExtractedEntity]]:
        """
        Extract entities from text.

        Args:
            text: The text to extract entities from
            doc_id: Document identifier for logging/debugging
            entity_types: Optional list of entity types to extract (default: all)

        Returns:
            Dict with keys: concepts, topics, methodologies, findings
            Each containing a list of ExtractedEntity objects
        """
        if not text or len(text.strip()) < 10:
            logger.warning(f"Text too short for entity extraction: {doc_id}")
            return {"concepts": [], "topics": [], "methodologies": [], "findings": []}

        # Test mode returns mock entities
        if self._test_mode:
            return self._build_test_entities(text, doc_id)

        try:
            logger.info(f"Extracting entities from document: {doc_id}")

            # Split text into batches
            batches = self._split_text_into_batches(text)
            logger.info(f"Split text into {len(batches)} batches for processing")

            # Process batches (with limited parallelism)
            batch_results = []

            # Process in groups of LLM_ENTITY_MAX_PARALLEL
            for i in range(0, len(batches), LLM_ENTITY_MAX_PARALLEL):
                batch_group = batches[i : i + LLM_ENTITY_MAX_PARALLEL]
                tasks = [
                    self._extract_from_batch(batch_text) for batch_text in batch_group
                ]
                results = await asyncio.gather(*tasks, return_exceptions=True)

                for j, result in enumerate(results):
                    batch_idx = i + j
                    if isinstance(result, Exception):
                        logger.error(
                            f"Error processing batch {batch_idx + 1}: {result}"
                        )
                        batch_results.append(
                            {
                                "concepts": [],
                                "topics": [],
                                "methodologies": [],
                                "findings": [],
                            }
                        )
                    else:
                        batch_results.append(result)
                        logger.debug(f"Completed batch {batch_idx + 1}/{len(batches)}")

            # Merge results from all batches
            merged = self._merge_batch_results(batch_results)

            # Deduplicate entities
            for key in merged:
                merged[key] = self._deduplicate(merged[key])

            # Convert to ExtractedEntity objects
            result = {"concepts": [], "topics": [], "methodologies": [], "findings": []}

            type_mapping = {
                "concepts": "Concept",
                "topics": "Topic",
                "methodologies": "Methodology",
                "findings": "Finding",
            }

            for entity_type, entities in merged.items():
                for entity in entities:
                    try:
                        extracted = ExtractedEntity(
                            name=entity.get("name", ""),
                            type=type_mapping.get(entity_type, "Concept"),
                            definition=entity.get("definition", ""),
                            confidence_score=float(entity.get("confidence", 0.7)),
                            source_text=entity.get("context", "")[:200]
                            if entity.get("context")
                            else None,
                            category=entity.get("category", "General"),
                        )
                        result[entity_type].append(extracted)
                    except Exception as e:
                        logger.warning(f"Failed to create ExtractedEntity: {e}")

            logger.info(
                f"Extracted {len(result['concepts'])} concepts, "
                f"{len(result['topics'])} topics, "
                f"{len(result['methodologies'])} methodologies, "
                f"{len(result['findings'])} findings"
            )

            return result

        except Exception as e:
            logger.error(f"Error in extract_entities for doc {doc_id}: {e}")
            return {"concepts": [], "topics": [], "methodologies": [], "findings": []}

    def _build_extraction_prompt(self, text: str) -> str:
        """Build the extraction prompt with JSON schema."""
        return ENTITY_EXTRACTION_PROMPT.format(text=text)

    def _parse_response(self, response_text: str) -> Dict[str, List[Dict]]:
        """
        Parse LLM response to structured entities.

        Args:
            response_text: Raw text response from LLM

        Returns:
            Dict with entity lists by type
        """
        result = {"concepts": [], "topics": [], "methodologies": [], "findings": []}

        if not response_text:
            return result

        try:
            # Try to parse as JSON directly
            extracted = json.loads(response_text.strip())
        except json.JSONDecodeError:
            # Try to extract JSON from response
            json_start = response_text.find("{")
            json_end = response_text.rfind("}") + 1

            if json_start >= 0 and json_end > json_start:
                json_str = response_text[json_start:json_end]
                try:
                    extracted = json.loads(json_str)
                except json.JSONDecodeError:
                    logger.warning("Failed to parse JSON from response")
                    return result
            else:
                logger.warning("No JSON found in response")
                return result

        # Extract entities from parsed JSON
        for entity_type in ["concepts", "topics", "methodologies", "findings"]:
            if entity_type in extracted:
                for entity in extracted[entity_type]:
                    if isinstance(entity, dict) and entity.get("name"):
                        result[entity_type].append(entity)

        return result

    async def _extract_from_batch(self, batch_text: str, retry_count: int = 0) -> Dict:
        """
        Extract from single batch with retry logic.

        Args:
            batch_text: Text content of the batch
            retry_count: Current retry attempt number

        Returns:
            Dict with extracted entities by type
        """
        empty_result = {
            "concepts": [],
            "topics": [],
            "methodologies": [],
            "findings": [],
        }

        if not self._model:
            logger.warning("Gemini model not initialized")
            return empty_result

        try:
            # Build prompt
            prompt = self._build_extraction_prompt(batch_text)

            # Configure generation
            generation_config = GenerationConfig(
                temperature=LLM_ENTITY_TEMPERATURE,
                max_output_tokens=4096,
            )

            logger.debug(
                f"Calling LLM for batch ({len(batch_text)} chars), attempt {retry_count + 1}/{MAX_RETRIES + 1}"
            )

            # Generate response
            response = generate_content(
                self._model,
                prompt,
                generation_config=generation_config,
            )

            response_text = response.text.strip() if response.text else ""

            logger.debug(f"LLM response length: {len(response_text)} chars")

            if not response_text:
                logger.warning("LLM returned empty response")
                return empty_result

            # Parse response
            result = self._parse_response(response_text)

            # Add IDs to entities
            for entity_type in result:
                for entity in result[entity_type]:
                    entity["id"] = self._generate_entity_id(
                        entity_type[:-1],  # Remove trailing 's'
                        entity.get("name", ""),
                    )

            total_entities = sum(len(v) for v in result.values())
            logger.info(
                f"Extracted {total_entities} entities from batch: "
                f"{len(result['concepts'])} concepts, {len(result['topics'])} topics, "
                f"{len(result['methodologies'])} methodologies, {len(result['findings'])} findings"
            )

            return result

        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {e}")
            if retry_count < MAX_RETRIES:
                wait_time = RETRY_BACKOFF_BASE * (2**retry_count)
                logger.info(
                    f"Retrying batch in {wait_time}s (attempt {retry_count + 2}/{MAX_RETRIES + 1})"
                )
                await asyncio.sleep(wait_time)
                return await self._extract_from_batch(batch_text, retry_count + 1)
            return empty_result

        except Exception as e:
            logger.error(f"Error in _extract_from_batch: {e}", exc_info=True)
            if retry_count < MAX_RETRIES:
                wait_time = RETRY_BACKOFF_BASE * (2**retry_count)
                logger.info(
                    f"Retrying batch in {wait_time}s after error (attempt {retry_count + 2}/{MAX_RETRIES + 1})"
                )
                await asyncio.sleep(wait_time)
                return await self._extract_from_batch(batch_text, retry_count + 1)
            return empty_result

    def _split_text_into_batches(self, text: str) -> List[str]:
        """
        Split text into batches respecting token limits.

        Uses paragraph boundaries when possible for cleaner splits.
        Includes overlap between batches for context continuity.

        Args:
            text: Full text to split

        Returns:
            List of text batches
        """
        batch_overlap = 200  # Tokens of overlap between batches

        batches = []
        paragraphs = [p.strip() for p in text.split("\n") if p.strip()]

        current_token_count = 0
        current_text = []

        for paragraph in paragraphs:
            para_tokens = self._count_tokens(paragraph)

            if current_token_count + para_tokens > LLM_ENTITY_BATCH_SIZE:
                if current_text:
                    batches.append(" ".join(current_text))

                # Keep some overlap for context
                overlap_paragraphs = []
                overlap_token_count = 0

                for prev_para in reversed(current_text):
                    prev_tokens = self._count_tokens(prev_para)
                    if overlap_token_count + prev_tokens > batch_overlap:
                        break
                    overlap_paragraphs.insert(0, prev_para)
                    overlap_token_count += prev_tokens

                current_text = overlap_paragraphs
                current_token_count = overlap_token_count

            current_text.append(paragraph)
            current_token_count += para_tokens

        if current_text:
            batches.append(" ".join(current_text))

        # Handle case where no paragraphs were found
        if not batches and text.strip():
            batches.append(text.strip())

        return batches

    def _generate_entity_id(self, prefix: str, name: str) -> str:
        """
        Generate hash-based entity ID.

        Args:
            prefix: Entity type prefix (e.g., 'concept', 'topic')
            name: Entity name

        Returns:
            Unique entity ID string
        """
        hash_str = hashlib.md5(name.lower().encode()).hexdigest()[:12]
        clean_prefix = prefix.lower().replace("_", "")
        return f"{clean_prefix}_{hash_str}"

    def _merge_batch_results(
        self, batch_results: List[Dict[str, List[Dict]]]
    ) -> Dict[str, List[Dict]]:
        """
        Merge results from multiple batches.

        Args:
            batch_results: List of extraction results from each batch

        Returns:
            Combined dict with all entities
        """
        merged = {"concepts": [], "topics": [], "methodologies": [], "findings": []}

        for batch_result in batch_results:
            for entity_type in merged:
                merged[entity_type].extend(batch_result.get(entity_type, []))

        return merged

    def _deduplicate(self, entities: List[Dict]) -> List[Dict]:
        """
        Deduplicate entities using exact name matching.

        Keeps entity with highest confidence when duplicates found.

        Args:
            entities: List of entity dicts

        Returns:
            Deduplicated list
        """
        if not entities:
            return []

        seen = {}
        for entity in entities:
            key = entity.get("name", "").lower().strip()
            if not key:
                continue

            if key not in seen:
                seen[key] = entity
            else:
                existing = seen[key]
                if entity.get("confidence", 0) > existing.get("confidence", 0):
                    # Merge contexts
                    existing_context = existing.get("context", "")[:100]
                    new_context = entity.get("context", "")[:100]
                    if existing_context and new_context:
                        entity["context"] = f"{existing_context} ... {new_context}"
                    entity["definition"] = entity.get("definition") or existing.get(
                        "definition"
                    )
                    seen[key] = entity
                else:
                    # Keep existing but merge context
                    existing_context = existing.get("context", "")[:100]
                    new_context = entity.get("context", "")[:100]
                    if existing_context and new_context:
                        existing["context"] = f"{existing_context} ... {new_context}"
                    existing["definition"] = existing.get("definition") or entity.get(
                        "definition"
                    )

        return list(seen.values())

    def _build_test_entities(
        self, text: str, doc_id: str
    ) -> Dict[str, List[ExtractedEntity]]:
        """
        Build mock entities for test mode.

        Args:
            text: Source text (used to determine which mock entities to return)
            doc_id: Document ID

        Returns:
            Dict with mock ExtractedEntity lists
        """
        text_lower = text.lower()
        concepts: List[ExtractedEntity] = []
        topics: List[ExtractedEntity] = []
        methodologies: List[ExtractedEntity] = []
        findings: List[ExtractedEntity] = []

        # Generate context-aware mock entities
        if "thermodynamics" in text_lower:
            concepts.append(
                ExtractedEntity(
                    name="First Law of Thermodynamics",
                    type="Concept",
                    definition="Energy is conserved in closed systems.",
                    confidence_score=0.9,
                    source_text="Energy cannot be created or destroyed.",
                    category="Physics",
                )
            )
            topics.append(
                ExtractedEntity(
                    name="Thermodynamics",
                    type="Topic",
                    definition="Study of heat, work, and energy transfer.",
                    confidence_score=0.85,
                    source_text="Thermodynamics is the study of heat and work.",
                    category="Physics",
                )
            )

        if "experimental" in text_lower:
            methodologies.append(
                ExtractedEntity(
                    name="Experimental analysis",
                    type="Methodology",
                    definition="Empirical testing to validate hypotheses.",
                    confidence_score=0.8,
                    source_text="Experimental analysis was conducted.",
                    category="Research Method",
                )
            )

        if "increased" in text_lower or "improved" in text_lower:
            findings.append(
                ExtractedEntity(
                    name="Efficiency improvement",
                    type="Finding",
                    definition="Observed increase in system efficiency.",
                    confidence_score=0.75,
                    source_text="Efficiency increased compared to baseline.",
                    category="Result",
                )
            )

        # Default test entity if nothing matched
        if not (concepts or topics or methodologies or findings):
            concepts.append(
                ExtractedEntity(
                    name="Test concept",
                    type="Concept",
                    definition="Placeholder concept for test mode.",
                    confidence_score=0.6,
                    source_text=text[:120] if len(text) > 120 else text,
                    category="General",
                )
            )

        return {
            "concepts": concepts,
            "topics": topics,
            "methodologies": methodologies,
            "findings": findings,
        }

    # ========================================================================
    # RELATIONSHIP EXTRACTION METHODS
    # ========================================================================

    def _build_relationship_prompt(
        self, text: str, entities: List[Dict[str, Any]]
    ) -> str:
        """
        Build prompt for relationship extraction between entities.

        Args:
            text: Source text to analyze
            entities: List of entity dicts with name, type, definition

        Returns:
            Formatted prompt string for LLM
        """
        # Build entity list for prompt (limit to 50 for clarity)
        entity_info = []
        for e in entities[:50]:
            name = e.get("name", "")
            entity_type = e.get("type", "Concept")
            definition = e.get("definition", "")[:100]
            entity_info.append(f"- {name} ({entity_type}): {definition}")

        entity_list_str = "\n".join(entity_info)

        return f"""<role>You are an expert academic relationship extractor. Your goal is to identify meaningful relationships between entities in academic text.</role>

<entities>
{entity_list_str}
</entities>

<task>Analyze the text and identify relationships between the listed entities. Look for:
- DEFINES: Entity A defines/explains entity B (e.g., "A concept that explains...")
- DEPENDS_ON: Entity A requires/needs entity B (e.g., "A depends on B", "A requires B")
- USES: Entity A uses/applies entity B (e.g., "A uses B", "A applies B")
- SUPPORTS: Entity A provides evidence for entity B (e.g., "A supports B", "A validates B")
- CONTRADICTS: Entity A conflicts with entity B (e.g., "A contradicts B", "A opposes B")
- EXTENDS: Entity A builds upon entity B (e.g., "A extends B", "A enhances B")
- IMPLEMENTS: Entity A is an implementation of entity B (e.g., "A implements B")
- REFERENCES: Entity A cites/mentions entity B (e.g., "A references B", "A cites B")
- RELATED_TO: Generic semantic relationship when more specific type is unclear
</task>

<output_format>
For each relationship provide:
- source: name of source entity (MUST exactly match one from the entity list)
- target: name of target entity (MUST exactly match one from the entity list)
- rel_type: one of the relationship types above
- confidence: 0.0-1.0 based on textual evidence strength
- evidence: brief text snippet (max 150 chars) showing the relationship

Return ONLY valid JSON: {{"relationships": [...]}}
No markdown, no explanations. Return empty array if no relationships found.
</output_format>

<input_text>
{text[:8000]}
</input_text>

<response_format>JSON Only</response_format>"""

    def _flatten_entities(self, entities: Dict[str, List[Any]]) -> List[Dict[str, Any]]:
        """
        Flatten entity dict structure to list for relationship extraction.

        Args:
            entities: Dict with keys concepts, topics, methodologies, findings

        Returns:
            Flat list of entity dicts with type added
        """
        type_mapping = {
            "concepts": "Concept",
            "topics": "Topic",
            "methodologies": "Methodology",
            "findings": "Finding",
        }

        flat_list = []
        for entity_type, entity_list in entities.items():
            mapped_type = type_mapping.get(entity_type, "Concept")
            for entity in entity_list:
                # Handle both ExtractedEntity objects and dicts
                if hasattr(entity, "model_dump"):
                    entity_dict = entity.model_dump()
                elif hasattr(entity, "__dict__"):
                    entity_dict = {
                        "name": getattr(entity, "name", ""),
                        "type": getattr(entity, "type", mapped_type),
                        "definition": getattr(entity, "definition", ""),
                    }
                else:
                    entity_dict = dict(entity)

                entity_dict["type"] = entity_dict.get("type", mapped_type)
                flat_list.append(entity_dict)

        return flat_list

    def _build_entity_name_map(
        self, entities: Dict[str, List[Any]]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Build a case-insensitive map of entity names to their data.

        Args:
            entities: Dict with keys concepts, topics, methodologies, findings

        Returns:
            Dict mapping lowercased name to entity dict
        """
        name_map = {}
        flat_entities = self._flatten_entities(entities)

        for entity in flat_entities:
            name = entity.get("name", "").lower().strip()
            if name:
                name_map[name] = entity

        return name_map

    async def extract_relationships(
        self,
        text: str,
        entities: Dict[str, List[Any]],
        doc_id: str = "unknown",
    ) -> List[Relationship]:
        """
        Extract relationships between previously extracted entities.

        This is the second pass of the two-pass extraction approach:
        1. First call: extract_entities() returns entities
        2. Second call: extract_relationships() with entities as context

        Args:
            text: The source text to analyze for relationships
            entities: Dict from extract_entities() with concepts, topics, etc.
            doc_id: Document identifier for logging

        Returns:
            List of validated Relationship objects
        """
        # Validate inputs
        flat_entities = self._flatten_entities(entities)
        if len(flat_entities) < 2:
            logger.debug(f"Not enough entities for relationship extraction: {doc_id}")
            return []

        if not text or len(text.strip()) < 50:
            logger.debug(f"Text too short for relationship extraction: {doc_id}")
            return []

        # Test mode returns mock relationships
        if self._test_mode:
            return self._build_test_relationships(flat_entities)

        if not self._model:
            logger.warning("Gemini model not initialized for relationship extraction")
            return []

        try:
            logger.info(
                f"Extracting relationships for {len(flat_entities)} entities from {doc_id}"
            )

            # Build prompt with entity context
            prompt = self._build_relationship_prompt(text, flat_entities)

            # Call LLM for relationship extraction
            raw_relationships = await self._extract_relationships_via_llm(prompt)

            # Build name map for validation
            name_map = self._build_entity_name_map(entities)

            # Validate and filter relationships
            validated = self._validate_relationships(raw_relationships, name_map)

            # Deduplicate
            deduplicated = self._deduplicate_relationships(validated)

            # Apply confidence threshold
            filtered = [
                r
                for r in deduplicated
                if r.confidence >= LLM_RELATIONSHIP_MIN_CONFIDENCE
            ]

            # Apply max limit
            filtered = filtered[:LLM_RELATIONSHIP_MAX_PER_DOCUMENT]

            logger.info(
                f"Extracted {len(filtered)} entity-entity relationships from {doc_id}"
            )

            return filtered

        except Exception as e:
            logger.error(f"Error in extract_relationships for doc {doc_id}: {e}")
            return []

    async def _extract_relationships_via_llm(
        self, prompt: str, retry_count: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Call LLM to extract relationships from the prompt.

        Args:
            prompt: Formatted relationship extraction prompt
            retry_count: Current retry attempt

        Returns:
            List of raw relationship dicts from LLM
        """
        try:
            generation_config = GenerationConfig(
                temperature=LLM_ENTITY_TEMPERATURE,
                max_output_tokens=4096,
            )

            logger.debug(
                f"Calling LLM for relationship extraction, attempt {retry_count + 1}/{MAX_RETRIES + 1}"
            )

            response = generate_content(
                self._model,
                prompt,
                generation_config=generation_config,
            )

            response_text = response.text.strip() if response.text else ""

            logger.debug(
                f"Relationship extraction response length: {len(response_text)} chars"
            )

            if not response_text:
                logger.warning("Relationship extraction returned empty response")
                return []

            # Parse JSON from response
            json_start = response_text.find("{")
            json_end = response_text.rfind("}") + 1

            if json_start >= 0 and json_end > json_start:
                json_str = response_text[json_start:json_end]

                try:
                    result = json.loads(json_str)
                    logger.info(
                        f"Successfully parsed relationship JSON: {list(result.keys())}"
                    )
                except json.JSONDecodeError as e:
                    logger.error(f"Relationship JSON decode error: {e}")
                    logger.error(f"JSON string that failed: {json_str[:500]}")
                    raise

                if "relationships" in result:
                    relationships = result["relationships"]
                    logger.info(
                        f"Extracted {len(relationships)} raw relationships from LLM"
                    )
                    return relationships

            logger.warning("No valid relationships JSON found in LLM response")
            return []

        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error in relationship extraction: {e}")
            if retry_count < MAX_RETRIES:
                wait_time = RETRY_BACKOFF_BASE * (2**retry_count)
                logger.info(
                    f"Retrying relationship extraction in {wait_time}s (attempt {retry_count + 2}/{MAX_RETRIES + 1})"
                )
                await asyncio.sleep(wait_time)
                return await self._extract_relationships_via_llm(
                    prompt, retry_count + 1
                )
            return []

        except Exception as e:
            logger.error(f"Error in _extract_relationships_via_llm: {e}", exc_info=True)
            if retry_count < MAX_RETRIES:
                wait_time = RETRY_BACKOFF_BASE * (2**retry_count)
                logger.info(
                    f"Retrying relationship extraction in {wait_time}s after error (attempt {retry_count + 2}/{MAX_RETRIES + 1})"
                )
                await asyncio.sleep(wait_time)
                return await self._extract_relationships_via_llm(
                    prompt, retry_count + 1
                )
            return []

    def _validate_relationships(
        self,
        raw_relationships: List[Dict[str, Any]],
        name_map: Dict[str, Dict[str, Any]],
    ) -> List[Relationship]:
        """
        Validate and convert raw relationship dicts to Relationship objects.

        Filters out:
        - Self-relationships (A -> A)
        - Relationships with entities not in the extracted set
        - Relationships with invalid types

        Args:
            raw_relationships: Raw dicts from LLM
            name_map: Case-insensitive map of entity names to entity data

        Returns:
            List of validated Relationship objects
        """
        validated = []

        for rel in raw_relationships:
            try:
                source_name = rel.get("source", "").strip()
                target_name = rel.get("target", "").strip()
                rel_type = rel.get("rel_type", "").upper()
                confidence = float(rel.get("confidence", 0.5))
                evidence = (
                    rel.get("evidence", "")[:300] if rel.get("evidence") else None
                )

                # Skip if missing required fields
                if not source_name or not target_name or not rel_type:
                    continue

                # Skip self-relationships
                if source_name.lower() == target_name.lower():
                    logger.debug(f"Skipping self-relationship: {source_name}")
                    continue

                # Skip if relationship type is invalid
                if rel_type not in RELATIONSHIP_TYPES:
                    logger.debug(f"Skipping invalid relationship type: {rel_type}")
                    continue

                # Validate source entity exists
                source_key = source_name.lower().strip()
                if source_key not in name_map:
                    logger.debug(f"Source entity not found: {source_name}")
                    continue

                # Validate target entity exists
                target_key = target_name.lower().strip()
                if target_key not in name_map:
                    logger.debug(f"Target entity not found: {target_name}")
                    continue

                # Clamp confidence to valid range
                confidence = max(0.0, min(1.0, confidence))

                # Create validated Relationship
                relationship = Relationship(
                    source_entity=name_map[source_key].get("name", source_name),
                    target_entity=name_map[target_key].get("name", target_name),
                    relationship_type=rel_type,
                    confidence=confidence,
                    evidence=evidence,
                )
                validated.append(relationship)

            except Exception as e:
                logger.warning(f"Failed to validate relationship: {e}")
                continue

        logger.debug(
            f"Validated {len(validated)} relationships from {len(raw_relationships)} raw"
        )
        return validated

    def _deduplicate_relationships(
        self, relationships: List[Relationship]
    ) -> List[Relationship]:
        """
        Deduplicate relationships, keeping highest confidence for duplicates.

        Also limits relationships per source entity.

        Args:
            relationships: List of validated relationships

        Returns:
            Deduplicated list of relationships
        """
        if not relationships:
            return []

        # Dedupe by (source, target, type) keeping highest confidence
        seen: Dict[Tuple[str, str, str], Relationship] = {}

        for rel in relationships:
            key = (
                rel.source_entity.lower(),
                rel.target_entity.lower(),
                rel.relationship_type,
            )

            if key not in seen:
                seen[key] = rel
            elif rel.confidence > seen[key].confidence:
                seen[key] = rel

        # Apply per-entity limit
        per_entity_count: Dict[str, int] = {}
        deduplicated = []

        # Sort by confidence descending to keep best relationships
        sorted_rels = sorted(seen.values(), key=lambda r: r.confidence, reverse=True)

        for rel in sorted_rels:
            source_key = rel.source_entity.lower()
            current_count = per_entity_count.get(source_key, 0)

            if current_count < LLM_RELATIONSHIP_MAX_PER_ENTITY:
                deduplicated.append(rel)
                per_entity_count[source_key] = current_count + 1

        if len(deduplicated) < len(seen):
            logger.debug(
                f"Relationship deduplication: {len(relationships)} -> {len(deduplicated)}"
            )

        return deduplicated

    async def extract_entities_and_relationships(
        self,
        text: str,
        doc_id: str = "unknown",
        entity_types: List[str] = None,
    ) -> Tuple[Dict[str, List[ExtractedEntity]], List[Relationship]]:
        """
        Combined extraction: entities first, then relationships.

        This is the recommended entry point for full extraction.
        Uses the two-pass approach:
        1. Extract entities from text
        2. Extract relationships between those entities

        Args:
            text: The text to extract from
            doc_id: Document identifier for logging
            entity_types: Optional list of entity types to extract (default: all)

        Returns:
            Tuple of (entities dict, relationships list)
        """
        # Step 1: Extract entities
        entities = await self.extract_entities(text, doc_id, entity_types)

        # Step 2: Extract relationships using the entities
        relationships = await self.extract_relationships(text, entities, doc_id)

        total_entities = sum(len(v) for v in entities.values())
        logger.info(
            f"Combined extraction for {doc_id}: "
            f"{total_entities} entities, {len(relationships)} relationships"
        )

        return entities, relationships

    def _build_test_relationships(
        self, entities: List[Dict[str, Any]]
    ) -> List[Relationship]:
        """
        Build mock relationships for test mode.

        Creates plausible relationships between extracted entities.

        Args:
            entities: List of entity dicts

        Returns:
            List of mock Relationship objects
        """
        relationships = []

        if len(entities) < 2:
            return relationships

        # Create some test relationships between the first few entities
        entity_names = [e.get("name", "") for e in entities if e.get("name")]

        if len(entity_names) >= 2:
            relationships.append(
                Relationship(
                    source_entity=entity_names[0],
                    target_entity=entity_names[1],
                    relationship_type="RELATED_TO",
                    confidence=0.75,
                    evidence="Test relationship for testing purposes.",
                )
            )

        if len(entity_names) >= 3:
            relationships.append(
                Relationship(
                    source_entity=entity_names[1],
                    target_entity=entity_names[2],
                    relationship_type="USES",
                    confidence=0.65,
                    evidence="Test relationship showing usage pattern.",
                )
            )

        return relationships
