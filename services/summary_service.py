# summary_service.py
# Service for generating document and module-level summaries with KG integration

# Provides automatic summarization of academic content at document and module
# levels using LLM. Integrates key entities from the knowledge graph and
# supports configurable summary lengths. Implements Redis caching with 24-hour
# TTL for performance optimization.

# @see: services/genai_client.py - Gemini client for LLM calls
# @see: api/graph_manager.py - Entity retrieval from knowledge graph
# @see: api/cache.py - Redis caching for summaries
# @note: Gracefully degrades when LLM or cache services unavailable

from __future__ import annotations

import hashlib
import logging
import re
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from services.genai_client import (
    GENAI_AVAILABLE,
    generate_content_with_thinking,
    get_genai_model,
)


# ============================================================================
# LOGGING
# ============================================================================

logger = logging.getLogger(__name__)


# ============================================================================
# CONFIGURATION CONSTANTS
# ============================================================================

# Summary length targets (approximate word counts)
BRIEF_WORD_COUNT = 100
STANDARD_WORD_COUNT = 250
DETAILED_WORD_COUNT = 500

# Cache configuration
CACHE_TTL_SECONDS = 24 * 60 * 60  # 24 hours
CACHE_PREFIX_DOCUMENT = "summary:doc"
CACHE_PREFIX_MODULE = "summary:mod"

# LLM configuration
DEFAULT_MODEL_NAME = "gemini-1.5-flash"


# ============================================================================
# ENUMS
# ============================================================================


class SummaryLength(str, Enum):
    """Summary length options with approximate word counts."""

    BRIEF = "brief"  # ~100 words
    STANDARD = "standard"  # ~250 words
    DETAILED = "detailed"  # ~500 words


# ============================================================================
# DATA MODELS
# ============================================================================


class DocumentSummary(BaseModel):
    """Summary of a single document with key entities and concepts."""

    document_id: str = Field(description="Unique document identifier")
    document_title: str = Field(description="Title of the document")
    summary: str = Field(description="Generated summary text")
    key_entities: List[str] = Field(
        default_factory=list,
        description="Key entities extracted from the document",
    )
    key_concepts: List[str] = Field(
        default_factory=list,
        description="Key concepts/themes in the document",
    )
    word_count: int = Field(ge=0, description="Word count of the summary")
    generated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when summary was generated",
    )
    cache_key: str = Field(default="", description="Cache key for this summary")


class ModuleSummary(BaseModel):
    """Summary of a module aggregating multiple documents."""

    module_id: str = Field(description="Unique module identifier")
    module_name: str = Field(description="Name of the module")
    summary: str = Field(description="Aggregated module summary")
    document_count: int = Field(ge=0, description="Number of documents in module")
    document_summaries: List[DocumentSummary] = Field(
        default_factory=list,
        description="Individual document summaries",
    )
    key_themes: List[str] = Field(
        default_factory=list,
        description="Key themes across all documents",
    )
    entity_frequency: Dict[str, int] = Field(
        default_factory=dict,
        description="Entity frequency counts across documents",
    )
    generated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when summary was generated",
    )


# ============================================================================
# PROMPT TEMPLATES
# ============================================================================

SUMMARY_PROMPT_TEMPLATE = """You are summarizing academic content for a learning platform.

Content to summarize:
{content}

Key entities from knowledge graph:
{entities}

Instructions:
1. Create a {length} summary (~{word_count} words)
2. Highlight the main concepts and themes
3. Reference key entities where relevant
4. Use clear, academic language
5. Structure with logical flow

Format your response EXACTLY as:
SUMMARY:
<your summary>

KEY_POINTS:
- Point 1
- Point 2
- Point 3

KEY_ENTITIES:
- Entity 1: brief relevance
- Entity 2: brief relevance
"""

MODULE_SYNTHESIS_PROMPT_TEMPLATE = """You are synthesizing an overview of an academic module.

Module: {module_name}

Document summaries:
{document_summaries}

Top entities and their frequencies:
{entity_frequencies}

Instructions:
1. Create a cohesive {length} overview (~{word_count} words)
2. Identify common themes across all documents
3. Highlight the most important concepts
4. Note connections between topics
5. Provide a learning roadmap for students

Format your response EXACTLY as:
OVERVIEW:
<your module overview>

KEY_THEMES:
- Theme 1
- Theme 2
- Theme 3

LEARNING_OBJECTIVES:
- Objective 1
- Objective 2
- Objective 3
"""


# ============================================================================
# SUMMARY SERVICE CLASS
# ============================================================================


class SummaryService:
    """
    Service for generating and caching document and module summaries.

    Provides LLM-based summarization with knowledge graph entity integration.
    Supports three summary lengths (brief, standard, detailed) and implements
    Redis caching for performance optimization.

    Example:
        from services.summary_service import SummaryService

        service = SummaryService()

        # Generate document summary
        doc_summary = await service.summarize_document(
            document_id="doc_123",
            length=SummaryLength.STANDARD,
        )

        # Generate module summary
        mod_summary = await service.summarize_module(
            module_id="mod_456",
            length=SummaryLength.DETAILED,
        )
    """

    def __init__(
        self,
        model_name: str = DEFAULT_MODEL_NAME,
        graph_manager=None,
        neo4j_driver=None,
    ):
        """
        Initialize SummaryService.

        Args:
            model_name: Gemini model to use for summarization.
            graph_manager: Optional GraphManager for entity retrieval.
            neo4j_driver: Optional Neo4j driver for direct queries.
        """
        self.model_name = model_name
        self._model = None
        self._graph_manager = graph_manager
        self._neo4j_driver = neo4j_driver
        self._cache = None

        logger.info(
            f"SummaryService initialized with model={model_name}, "
            f"genai_available={GENAI_AVAILABLE}"
        )

    def _get_model(self) -> Any:
        """Get or initialize the Gemini model."""
        if self._model is None:
            self._model = get_genai_model(self.model_name)
        return self._model

    def _get_cache(self):
        """Get the Redis cache client with lazy initialization."""
        if self._cache is None:
            try:
                from api.cache import redis_client

                self._cache = redis_client
            except ImportError:
                try:
                    from cache import redis_client

                    self._cache = redis_client
                except ImportError:
                    logger.warning("Cache module not available, caching disabled")
                    self._cache = None
        return self._cache

    def _get_word_count(self, length: SummaryLength) -> int:
        """Get target word count for summary length."""
        if length == SummaryLength.BRIEF:
            return BRIEF_WORD_COUNT
        elif length == SummaryLength.DETAILED:
            return DETAILED_WORD_COUNT
        return STANDARD_WORD_COUNT

    def _generate_cache_key(
        self,
        prefix: str,
        item_id: str,
        length: SummaryLength,
        content_hash: str = "",
    ) -> str:
        """Generate a cache key for a summary."""
        return f"{prefix}:{item_id}:{length.value}:{content_hash[:8]}"

    def _compute_content_hash(self, content: str) -> str:
        """Compute a hash of the content for cache invalidation."""
        return hashlib.md5(content.encode("utf-8")).hexdigest()

    async def _get_cached_summary(
        self,
        cache_key: str,
    ) -> Optional[Dict[str, Any]]:
        """Retrieve a cached summary if available."""
        cache = self._get_cache()
        if cache is None:
            return None

        try:
            data = cache.get(cache_key)
            if data:
                logger.debug(f"Cache hit for {cache_key}")
                return data
        except Exception as e:
            logger.debug(f"Cache lookup failed for {cache_key}: {e}")

        return None

    def _cache_summary(
        self,
        cache_key: str,
        summary_data: Dict[str, Any],
        ttl: int = CACHE_TTL_SECONDS,
    ) -> bool:
        """Store a summary in cache."""
        cache = self._get_cache()
        if cache is None:
            return False

        try:
            return cache.set(cache_key, summary_data, ttl=ttl)
        except Exception as e:
            logger.debug(f"Cache storage failed for {cache_key}: {e}")
            return False

    def invalidate_cache(self, cache_key: str) -> bool:
        """Invalidate a specific cached summary."""
        cache = self._get_cache()
        if cache is None:
            return False

        try:
            return cache.delete(cache_key)
        except Exception as e:
            logger.debug(f"Cache invalidation failed for {cache_key}: {e}")
            return False

    def invalidate_document_cache(self, document_id: str) -> int:
        """Invalidate all cached summaries for a document."""
        cache = self._get_cache()
        if cache is None:
            return 0

        pattern = f"{CACHE_PREFIX_DOCUMENT}:{document_id}:*"
        return cache.delete_pattern(pattern)

    def invalidate_module_cache(self, module_id: str) -> int:
        """Invalidate all cached summaries for a module."""
        cache = self._get_cache()
        if cache is None:
            return 0

        pattern = f"{CACHE_PREFIX_MODULE}:{module_id}:*"
        return cache.delete_pattern(pattern)

    async def _get_document_content(
        self,
        document_id: str,
    ) -> tuple[str, str, List[str]]:
        """
        Retrieve document content and entities from Neo4j.

        Args:
            document_id: Document ID to retrieve.

        Returns:
            Tuple of (content, title, entity_names)
        """
        if self._neo4j_driver is None:
            try:
                from api.neo4j_config import neo4j_driver

                self._neo4j_driver = neo4j_driver
            except ImportError:
                logger.warning("Neo4j driver not available")
                return "", "", []

        if self._neo4j_driver is None:
            return "", "", []

        try:
            with self._neo4j_driver.session() as session:
                # Get document and its chunks
                result = session.run(
                    """
                    MATCH (d:Document {id: $doc_id})
                    OPTIONAL MATCH (d)-[:HAS_CHUNK]->(c:Chunk)
                    OPTIONAL MATCH (c)-[:MENTIONS]->(e)
                    WHERE e:Topic OR e:Concept OR e:Methodology OR e:Finding
                    WITH d, collect(DISTINCT c.text) as chunks,
                         collect(DISTINCT e.name) as entities
                    RETURN d.id as id, d.title as title, d.module_id as module_id,
                           chunks, entities
                    """,
                    {"doc_id": document_id},
                )
                record = result.single()

                if record:
                    chunks = record["chunks"] or []
                    content = "\n\n".join([c for c in chunks if c])
                    title = record["title"] or document_id
                    entities = record["entities"] or []
                    return content, title, entities

        except Exception as e:
            logger.warning(f"Failed to get document content for {document_id}: {e}")

        return "", "", []

    async def _get_module_documents(
        self,
        module_id: str,
    ) -> tuple[str, List[str]]:
        """
        Get module name and list of document IDs.

        Args:
            module_id: Module ID to retrieve.

        Returns:
            Tuple of (module_name, document_ids)
        """
        if self._neo4j_driver is None:
            try:
                from api.neo4j_config import neo4j_driver

                self._neo4j_driver = neo4j_driver
            except ImportError:
                logger.warning("Neo4j driver not available")
                return "", []

        if self._neo4j_driver is None:
            return "", []

        try:
            with self._neo4j_driver.session() as session:
                result = session.run(
                    """
                    MATCH (d:Document)
                    WHERE d.module_id = $module_id
                    RETURN d.id as id, d.title as title
                    ORDER BY d.title
                    """,
                    {"module_id": module_id},
                )

                doc_ids = []
                for record in result:
                    doc_ids.append(record["id"])

                # Module name - use module_id as fallback
                module_name = module_id

                return module_name, doc_ids

        except Exception as e:
            logger.warning(f"Failed to get module documents for {module_id}: {e}")

        return "", []

    def _parse_summary_response(
        self,
        response_text: str,
    ) -> Dict[str, Any]:
        """Parse the structured LLM response into components."""
        result = {
            "summary": "",
            "key_points": [],
            "key_entities": [],
        }

        if not response_text:
            return result

        # Extract SUMMARY section
        summary_match = re.search(
            r"SUMMARY:\s*(.*?)(?=KEY_POINTS:|KEY_ENTITIES:|$)",
            response_text,
            re.DOTALL | re.IGNORECASE,
        )
        if summary_match:
            result["summary"] = summary_match.group(1).strip()

        # Extract KEY_POINTS section
        key_points_match = re.search(
            r"KEY_POINTS:\s*(.*?)(?=KEY_ENTITIES:|$)",
            response_text,
            re.DOTALL | re.IGNORECASE,
        )
        if key_points_match:
            points_text = key_points_match.group(1).strip()
            points = re.findall(r"[-•*]\s*(.+?)(?=\n[-•*]|\n\n|$)", points_text)
            result["key_points"] = [p.strip() for p in points if p.strip()]

        # Extract KEY_ENTITIES section
        entities_match = re.search(
            r"KEY_ENTITIES:\s*(.*?)$",
            response_text,
            re.DOTALL | re.IGNORECASE,
        )
        if entities_match:
            entities_text = entities_match.group(1).strip()
            # Extract entity names (before the colon)
            entities = re.findall(r"[-•*]\s*([^:]+):", entities_text)
            result["key_entities"] = [e.strip() for e in entities if e.strip()]

        return result

    def _parse_module_response(
        self,
        response_text: str,
    ) -> Dict[str, Any]:
        """Parse the module synthesis LLM response."""
        result = {
            "overview": "",
            "key_themes": [],
            "learning_objectives": [],
        }

        if not response_text:
            return result

        # Extract OVERVIEW section
        overview_match = re.search(
            r"OVERVIEW:\s*(.*?)(?=KEY_THEMES:|LEARNING_OBJECTIVES:|$)",
            response_text,
            re.DOTALL | re.IGNORECASE,
        )
        if overview_match:
            result["overview"] = overview_match.group(1).strip()

        # Extract KEY_THEMES section
        themes_match = re.search(
            r"KEY_THEMES:\s*(.*?)(?=LEARNING_OBJECTIVES:|$)",
            response_text,
            re.DOTALL | re.IGNORECASE,
        )
        if themes_match:
            themes_text = themes_match.group(1).strip()
            themes = re.findall(r"[-•*]\s*(.+?)(?=\n[-•*]|\n\n|$)", themes_text)
            result["key_themes"] = [t.strip() for t in themes if t.strip()]

        # Extract LEARNING_OBJECTIVES section
        objectives_match = re.search(
            r"LEARNING_OBJECTIVES:\s*(.*?)$",
            response_text,
            re.DOTALL | re.IGNORECASE,
        )
        if objectives_match:
            obj_text = objectives_match.group(1).strip()
            objectives = re.findall(r"[-•*]\s*(.+?)(?=\n[-•*]|\n\n|$)", obj_text)
            result["learning_objectives"] = [o.strip() for o in objectives if o.strip()]

        return result

    async def summarize_document(
        self,
        document_id: str,
        length: SummaryLength = SummaryLength.STANDARD,
        force_regenerate: bool = False,
    ) -> DocumentSummary:
        """
        Generate or retrieve a cached summary for a document.

        Args:
            document_id: Document ID to summarize.
            length: Summary length (brief, standard, detailed).
            force_regenerate: Force regeneration even if cached.

        Returns:
            DocumentSummary with summary and metadata.
        """
        logger.info(f"Summarizing document {document_id} (length={length.value})")

        # Get document content and entities
        content, title, entities = await self._get_document_content(document_id)

        if not content:
            logger.warning(f"No content found for document {document_id}")
            return DocumentSummary(
                document_id=document_id,
                document_title=title or document_id,
                summary="No content available for summarization.",
                key_entities=[],
                key_concepts=[],
                word_count=0,
                cache_key="",
            )

        # Generate cache key
        content_hash = self._compute_content_hash(content)
        cache_key = self._generate_cache_key(
            CACHE_PREFIX_DOCUMENT,
            document_id,
            length,
            content_hash,
        )

        # Check cache unless force regenerate
        if not force_regenerate:
            cached = await self._get_cached_summary(cache_key)
            if cached:
                return DocumentSummary(**cached)

        # Get model
        model = self._get_model()
        if model is None:
            logger.warning("GenAI not available, returning fallback summary")
            return self._build_fallback_document_summary(
                document_id, title, content, entities, length, cache_key
            )

        # Build and execute prompt
        word_count = self._get_word_count(length)
        entities_str = ", ".join(entities[:20]) if entities else "None identified"

        prompt = SUMMARY_PROMPT_TEMPLATE.format(
            content=content[:10000],  # Limit content length
            entities=entities_str,
            length=length.value,
            word_count=word_count,
        )

        try:
            response = generate_content_with_thinking(model, prompt)
            response_text = response.text

            # Parse response
            parsed = self._parse_summary_response(response_text)

            summary = DocumentSummary(
                document_id=document_id,
                document_title=title,
                summary=parsed["summary"],
                key_entities=parsed["key_entities"],
                key_concepts=parsed["key_points"],
                word_count=len(parsed["summary"].split()),
                cache_key=cache_key,
            )

            # Cache the result
            self._cache_summary(cache_key, summary.model_dump())

            logger.info(
                f"Document summary generated: {document_id}, words={summary.word_count}"
            )

            return summary

        except Exception as e:
            logger.error(f"LLM summarization failed for {document_id}: {e}")
            return self._build_fallback_document_summary(
                document_id, title, content, entities, length, cache_key
            )

    def _build_fallback_document_summary(
        self,
        document_id: str,
        title: str,
        content: str,
        entities: List[str],
        length: SummaryLength,
        cache_key: str,
    ) -> DocumentSummary:
        """Build a fallback summary when LLM is unavailable."""
        word_count = self._get_word_count(length)

        # Extract first N words as a simple summary
        words = content.split()[:word_count]
        summary = " ".join(words)
        if len(content.split()) > word_count:
            summary += "..."

        return DocumentSummary(
            document_id=document_id,
            document_title=title,
            summary=f"[Auto-extracted] {summary}",
            key_entities=entities[:5],
            key_concepts=[],
            word_count=len(summary.split()),
            cache_key=cache_key,
        )

    async def summarize_module(
        self,
        module_id: str,
        length: SummaryLength = SummaryLength.STANDARD,
        include_document_summaries: bool = True,
        force_regenerate: bool = False,
    ) -> ModuleSummary:
        """
        Generate or retrieve a cached summary for a module.

        Aggregates summaries from all documents in the module and
        synthesizes a cohesive module-level overview.

        Args:
            module_id: Module ID to summarize.
            length: Summary length (brief, standard, detailed).
            include_document_summaries: Include individual doc summaries.
            force_regenerate: Force regeneration even if cached.

        Returns:
            ModuleSummary with aggregated summary and metadata.
        """
        logger.info(f"Summarizing module {module_id} (length={length.value})")

        # Get module documents
        module_name, doc_ids = await self._get_module_documents(module_id)

        if not doc_ids:
            logger.warning(f"No documents found for module {module_id}")
            return ModuleSummary(
                module_id=module_id,
                module_name=module_name or module_id,
                summary="No documents available for summarization.",
                document_count=0,
                document_summaries=[],
                key_themes=[],
                entity_frequency={},
            )

        # Generate individual document summaries
        doc_summaries = []
        entity_freq: Dict[str, int] = {}

        for doc_id in doc_ids:
            doc_summary = await self.summarize_document(
                document_id=doc_id,
                length=SummaryLength.BRIEF,  # Use brief for components
                force_regenerate=force_regenerate,
            )
            doc_summaries.append(doc_summary)

            # Track entity frequencies
            for entity in doc_summary.key_entities:
                entity_freq[entity] = entity_freq.get(entity, 0) + 1

        # Sort entities by frequency
        sorted_entities = sorted(
            entity_freq.items(),
            key=lambda x: x[1],
            reverse=True,
        )

        # Generate cache key using all doc summaries
        combined_content = "".join([ds.summary for ds in doc_summaries])
        content_hash = self._compute_content_hash(combined_content)
        cache_key = self._generate_cache_key(
            CACHE_PREFIX_MODULE,
            module_id,
            length,
            content_hash,
        )

        # Check cache unless force regenerate
        if not force_regenerate:
            cached = await self._get_cached_summary(cache_key)
            if cached:
                # Update with fresh doc_summaries if requested
                result = ModuleSummary(**cached)
                if include_document_summaries:
                    result.document_summaries = doc_summaries
                return result

        # Synthesize module overview
        model = self._get_model()
        if model is None:
            logger.warning("GenAI not available, returning aggregated summary")
            return self._build_fallback_module_summary(
                module_id,
                module_name,
                doc_summaries,
                sorted_entities,
                length,
                include_document_summaries,
            )

        # Build synthesis prompt
        word_count = self._get_word_count(length)
        doc_summaries_text = "\n\n".join(
            [f"- {ds.document_title}: {ds.summary}" for ds in doc_summaries]
        )
        entity_freq_text = ", ".join(
            [f"{e[0]} ({e[1]}x)" for e in sorted_entities[:15]]
        )

        prompt = MODULE_SYNTHESIS_PROMPT_TEMPLATE.format(
            module_name=module_name,
            document_summaries=doc_summaries_text,
            entity_frequencies=entity_freq_text,
            length=length.value,
            word_count=word_count,
        )

        try:
            response = generate_content_with_thinking(model, prompt)
            response_text = response.text

            # Parse response
            parsed = self._parse_module_response(response_text)

            module_summary = ModuleSummary(
                module_id=module_id,
                module_name=module_name,
                summary=parsed["overview"],
                document_count=len(doc_summaries),
                document_summaries=doc_summaries if include_document_summaries else [],
                key_themes=parsed["key_themes"],
                entity_frequency=dict(sorted_entities[:20]),
            )

            # Cache the result (without doc_summaries to save space)
            cache_data = module_summary.model_dump()
            cache_data["document_summaries"] = []  # Don't cache these
            self._cache_summary(cache_key, cache_data)

            logger.info(
                f"Module summary generated: {module_id}, "
                f"docs={module_summary.document_count}"
            )

            return module_summary

        except Exception as e:
            logger.error(f"LLM module synthesis failed for {module_id}: {e}")
            return self._build_fallback_module_summary(
                module_id,
                module_name,
                doc_summaries,
                sorted_entities,
                length,
                include_document_summaries,
            )

    def _build_fallback_module_summary(
        self,
        module_id: str,
        module_name: str,
        doc_summaries: List[DocumentSummary],
        sorted_entities: List[tuple[str, int]],
        length: SummaryLength,
        include_doc_summaries: bool,
    ) -> ModuleSummary:
        """Build a fallback module summary when LLM is unavailable."""
        # Aggregate summaries
        summary_parts = []
        for ds in doc_summaries[:5]:  # Limit to first 5
            summary_parts.append(f"• {ds.document_title}: {ds.summary[:100]}...")

        summary = "This module covers:\n" + "\n".join(summary_parts)

        return ModuleSummary(
            module_id=module_id,
            module_name=module_name,
            summary=summary,
            document_count=len(doc_summaries),
            document_summaries=doc_summaries if include_doc_summaries else [],
            key_themes=[e[0] for e in sorted_entities[:5]],
            entity_frequency=dict(sorted_entities[:20]),
        )

    async def summarize_chunks(
        self,
        chunk_ids: List[str],
        context: Optional[str] = None,
        length: SummaryLength = SummaryLength.BRIEF,
    ) -> str:
        """
        Summarize a specific set of chunks.

        Args:
            chunk_ids: List of chunk IDs to summarize.
            context: Optional context for the summary.
            length: Summary length.

        Returns:
            Summary text.
        """
        if not chunk_ids:
            return ""

        if self._neo4j_driver is None:
            try:
                from api.neo4j_config import neo4j_driver

                self._neo4j_driver = neo4j_driver
            except ImportError:
                return "Unable to retrieve chunk content."

        if self._neo4j_driver is None:
            return "Unable to retrieve chunk content."

        try:
            with self._neo4j_driver.session() as session:
                result = session.run(
                    """
                    MATCH (c:Chunk)
                    WHERE c.id IN $chunk_ids
                    RETURN c.text as text
                    ORDER BY c.id
                    """,
                    {"chunk_ids": chunk_ids},
                )

                chunks = [record["text"] for record in result if record["text"]]

                if not chunks:
                    return ""

                content = "\n\n".join(chunks)

                # Use LLM if available
                model = self._get_model()
                if model is None:
                    # Fallback: return truncated content
                    word_count = self._get_word_count(length)
                    words = content.split()[:word_count]
                    return " ".join(words)

                word_count = self._get_word_count(length)
                prompt = f"""Summarize the following content in approximately {word_count} words:

{content[:5000]}

{f"Context: {context}" if context else ""}

Provide a concise, coherent summary:"""

                response = generate_content_with_thinking(model, prompt)
                return response.text.strip()

        except Exception as e:
            logger.error(f"Chunk summarization failed: {e}")
            return ""


# ============================================================================
# FACTORY FUNCTION
# ============================================================================


def create_summary_service(
    model_name: str = DEFAULT_MODEL_NAME,
    graph_manager=None,
    neo4j_driver=None,
) -> SummaryService:
    """
    Factory function to create SummaryService.

    Args:
        model_name: Gemini model to use for summarization.
        graph_manager: Optional GraphManager for entity retrieval.
        neo4j_driver: Optional Neo4j driver for direct queries.

    Returns:
        Configured SummaryService instance.
    """
    return SummaryService(
        model_name=model_name,
        graph_manager=graph_manager,
        neo4j_driver=neo4j_driver,
    )
