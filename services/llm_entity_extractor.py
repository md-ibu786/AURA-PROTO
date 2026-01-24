# llm_entity_extractor.py
# LLM-powered entity extraction using Google Gemini for knowledge graph construction

# Extracts structured entities (Topic, Concept, Methodology, Finding) from document
# chunks using Gemini with configurable prompts, confidence scoring, and validation.
# Ported from AURA-CHAT/backend/llm_entity_extractor.py for consistency.

# @see: api/kg_processor.py - Integration point for entity extraction
# @note: Uses google-generativeai SDK, not Vertex AI (unlike AURA-CHAT)

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import time
from typing import Dict, List, Literal, Optional, Any

from pydantic import BaseModel, Field

# ============================================================================
# CONFIGURATION CONSTANTS
# ============================================================================

LLM_ENTITY_BATCH_SIZE = 3000  # Tokens per batch
LLM_ENTITY_MAX_PARALLEL = 2  # Max concurrent requests
MAX_RETRIES = 3  # Retry attempts
RETRY_BACKOFF_BASE = 2.0  # Exponential backoff base
LLM_ENTITY_TEMPERATURE = 0.2  # Generation temperature

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

    def __init__(self, model_name: str = "gemini-1.5-flash", api_key: str = None):
        """
        Initialize with Gemini model.

        Args:
            model_name: Name of the Gemini model to use (default: gemini-1.5-flash)
            api_key: Google API key (defaults to GEMINI_API_KEY or GOOGLE_API_KEY env var)
        """
        self.model_name = model_name
        self.api_key = (
            api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        )
        self._test_mode = os.getenv("AURA_TEST_MODE", "").lower() == "true"
        self._model = None
        self._encoding = None

        # Initialize tiktoken for token counting
        try:
            import tiktoken

            self._encoding = tiktoken.get_encoding("cl100k_base")
        except ImportError:
            logger.warning("tiktoken not available, using whitespace tokenization")

        if not self._test_mode:
            self._initialize_model()
        else:
            logger.info("LLMEntityExtractor initialized in test mode")

    def _initialize_model(self):
        """Initialize the Gemini model."""
        try:
            import google.generativeai as genai

            if not self.api_key:
                logger.warning("No API key configured for Gemini")
                return

            genai.configure(api_key=self.api_key)
            self._model = genai.GenerativeModel(self.model_name)
            logger.info(f"Initialized LLMEntityExtractor with model: {self.model_name}")
        except ImportError:
            logger.error("google-generativeai not installed")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini model: {e}")

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
            import google.generativeai as genai

            # Build prompt
            prompt = self._build_extraction_prompt(batch_text)

            # Configure generation
            generation_config = genai.GenerationConfig(
                temperature=LLM_ENTITY_TEMPERATURE,
                max_output_tokens=4096,
            )

            logger.debug(
                f"Calling LLM for batch ({len(batch_text)} chars), attempt {retry_count + 1}/{MAX_RETRIES + 1}"
            )

            # Generate response
            response = self._model.generate_content(
                prompt, generation_config=generation_config
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

        current_tokens = []
        current_text = []

        for paragraph in paragraphs:
            para_tokens = self._count_tokens(paragraph)

            if len(current_tokens) + para_tokens > LLM_ENTITY_BATCH_SIZE:
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
                current_tokens = (
                    [self._count_tokens(" ".join(overlap_paragraphs))]
                    if overlap_paragraphs
                    else []
                )

            current_text.append(paragraph)
            current_tokens.append(para_tokens)

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
