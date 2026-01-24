"""
============================================================================
FILE: kg_processor.py
LOCATION: api/kg_processor.py
============================================================================

PURPOSE:
    Core Knowledge Graph Processor for converting documents to knowledge graphs.
    Handles document ingestion, embedding generation, entity extraction, and
    Neo4j storage with module_id tagging.

ROLE IN PROJECT:
    This is the document-to-KG conversion engine for Phase 2 of AURA M2KG.
    It orchestrates the entire pipeline from raw document to indexed knowledge graph.

KEY COMPONENTS:
    - KnowledgeGraphProcessor: Main processor class
    - Document ingestion pipeline (PDF, DOCX, TXT)
    - Module_id propagation through all nodes
    - Gemini integration for embeddings and entity extraction
    - Progress tracking for long-running operations

SUPPORTED FILE FORMATS:
    - PDF: PyMuPDF (fitz) for text extraction
    - DOCX: python-docx via DocxParser (09-07-PLAN)
    - TXT: Direct file reading with encoding fallback

DEPENDENCIES:
    - External: neo4j, PyMuPDF (fitz), python-docx, python-dotenv
    - Internal: neo4j_config for driver, config for settings
    - services/document_parsers/docx_parser.py - DOCX parsing

USAGE:
    from api.kg_processor import KnowledgeGraphProcessor
    from api.neo4j_config import neo4j_driver

    # Initialize with dependencies
    processor = KnowledgeGraphProcessor(neo4j_driver, gemini_client)

    # Process a single document
    result = await processor.process_document(document_id, module_id, user_id)

    # Process multiple documents in batch
    results = await processor.process_batch([doc_id1, doc_id2], module_id, user_id)

ENVIRONMENT VARIABLES:
    - GEMINI_API_KEY: Google Gemini API key for embeddings and entity extraction
    - CHUNK_SIZE: Token size for text chunking (default: 800)
    - CHUNK_OVERLAP: Token overlap between chunks (default: 100)
============================================================================
"""

import os
import sys
import json
import hashlib
import asyncio
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional, Callable, Union
from enum import Enum

# PDF and text parsing
import fitz  # PyMuPDF for PDF parsing

# Add parent directory to path for internal imports
sys.path.insert(0, os.path.dirname(__file__))

from neo4j_config import neo4j_driver
from logging_config import logger

# Import chunking utilities (ported from AURA-CHAT)
try:
    from services.chunking_utils import (
        count_tokens,
        split_into_sentences,
        normalize_text,
    )
except ImportError:
    # Fallback if services module not in path
    import sys

    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from services.chunking_utils import (
        count_tokens,
        split_into_sentences,
        normalize_text,
    )

# Import LLM entity extractor (ported from AURA-CHAT)
try:
    from services.llm_entity_extractor import (
        LLMEntityExtractor,
        ExtractedEntity,
        Relationship as EntityRelationship,
    )
except ImportError:
    # Fallback if services module not in path
    import sys

    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from services.llm_entity_extractor import (
        LLMEntityExtractor,
        ExtractedEntity,
        Relationship as EntityRelationship,
    )

# Import embedding service for entity embeddings
try:
    from services.embeddings import EmbeddingService
except ImportError:
    import sys

    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from services.embeddings import EmbeddingService

# Import semantic entity deduplicator (09-06-PLAN)
try:
    from services.entity_deduplicator import EntityDeduplicator
except ImportError:
    import sys

    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from services.entity_deduplicator import EntityDeduplicator

# Import DOCX parser (09-07-PLAN)
try:
    from services.document_parsers.docx_parser import (
        DocxParser,
        ParsedDocument as DocxParsedDocument,
        DocxParseError,
        CorruptedDocxError,
        PasswordProtectedDocxError,
        EmptyDocxError,
    )
except ImportError:
    import sys

    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from services.document_parsers.docx_parser import (
        DocxParser,
        ParsedDocument as DocxParsedDocument,
        DocxParseError,
        CorruptedDocxError,
        PasswordProtectedDocxError,
        EmptyDocxError,
    )

# Import extraction templates (11-03-PLAN)
try:
    from services.extraction_templates import (
        TemplateExtractor,
        TemplateRegistry,
        ExtractionOptions,
        get_template_registry,
        get_template_extractor,
    )
except ImportError:
    import sys

    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from services.extraction_templates import (
        TemplateExtractor,
        TemplateRegistry,
        ExtractionOptions,
        get_template_registry,
        get_template_extractor,
    )

# ============================================================================
# CHUNKING CONFIGURATION
# ============================================================================

# LLM prompt for semantic splitting
CHUNK_BY_SEMANTIC_SPLIT = """
You are a text segmentation expert. Given the following document content,
identify logical breaks where the topic changes significantly.

Document:
{content}

Instructions:
1. Split into chunks at natural topic boundaries
2. Keep related concepts together
3. Aim for chunks of 500-1000 tokens
4. Return JSON array of chunks with brief descriptions
5. Each chunk should be coherent and self-contained

Output format (JSON only, no markdown):
[
  {{"chunk_index": 0, "content": "...", "description": "..."}},
  {{"chunk_index": 1, "content": "...", "description": "..."}}
]
"""

# Chunk size configuration
# NOTE: These are now overridden by config values if available
CHUNK_SIZE = 800  # Target tokens per chunk
CHUNK_OVERLAP_SIZE = 100  # Overlap tokens between chunks
MIN_CHUNK_SIZE = 500  # Minimum tokens for valid chunk
MAX_CHUNK_SIZE = 1000  # Maximum tokens for valid chunk
SEMANTIC_SIMILARITY_THRESHOLD = 0.3  # Cosine distance threshold for boundaries

# Hierarchical chunking configuration (ported from AURA-CHAT)
# Parent chunks provide section-level context for LLM, child chunks for precise search
PARENT_CHUNK_SIZE = 1500  # ~1500 tokens per parent chunk (3-4 paragraphs)
CHILD_CHUNK_SIZE = 800  # ~800 tokens per child chunk
CHILD_CHUNK_OVERLAP = 200  # Overlap between child chunks for context continuity


# ============================================================================
# ENTITY EXTRACTION CONFIGURATION
# ============================================================================

# Entity extraction prompt (aligned with AURA-CHAT/backend/llm_entity_extractor.py)
ENTITY_EXTRACTION_PROMPT = """
You are a knowledge graph expert. Extract entities from the following text.

Text:
{chunk_text}

Extract entities of these types:
- TOPIC: Main subject areas (e.g., "Machine Learning", "Database Systems")
- CONCEPT: Specific ideas, theories, or definitions (e.g., "Neural Network", "SQL Injection")
- METHODOLOGY: Approaches, techniques, or methods (e.g., "Backpropagation", "CRUD Operations")
- FINDING: Important discoveries, conclusions, or results

Return JSON array with this schema:
[
  {{
    "name": "Entity Name (expand acronyms)",
    "category": "TOPIC|CONCEPT|METHODOLOGY|FINDING",
    "definition": "Brief definition (1-2 sentences)",
    "context_snippet": "Source text excerpt (max 150 chars)",
    "confidence": 0.95
  }}
]

Only extract entities that are explicitly defined or clearly explained in the text.
"""

# Entity deduplication settings (from llm_entity_extractor.py patterns)
ENTITY_BATCH_SIZE = 3000  # Tokens per batch for entity extraction
ENTITY_MAX_PARALLEL = 2  # Max concurrent LLM requests
ENTITY_DEDUP_SIMILARITY_THRESHOLD = 0.85  # Cosine similarity threshold

# Relationship types for entity-entity relationships
ENTITY_RELATIONSHIP_TYPES = [
    "DEFINES",
    "DEPENDS_ON",
    "USES",
    "SUPPORTS",
    "CONTRADICTS",
    "DERIVED_FROM",
    "INSTANCE_OF",
    "CAUSES",
    "RELATED_TO",
]


class EntityType(str, Enum):
    """Supported entity types for knowledge graph extraction."""

    TOPIC = "Topic"
    CONCEPT = "Concept"
    METHODOLOGY = "Methodology"
    FINDING = "Finding"
    DEFINITION = "Definition"
    CITATION = "Citation"


@dataclass
class Entity:
    """Represents an extracted entity from document content."""

    id: str
    name: str
    entity_type: EntityType
    definition: str = ""
    properties: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[List[float]] = None


@dataclass
class Relationship:
    """Represents a relationship between entities."""

    source_id: str
    target_id: str
    rel_type: str
    properties: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Chunk:
    """Represents a text chunk with embedding."""

    id: str
    text: str
    index: int
    token_count: int
    embedding: Optional[List[float]] = None
    entities: List[Entity] = field(default_factory=list)


@dataclass
class ParentChunk:
    """
    Represents a parent chunk containing child chunks for hierarchical RAG.

    Parent chunks provide section-level context (~1500 tokens) while child
    chunks are used for precise search (~800 tokens with overlap). When a
    child matches a query, its parent provides expanded context to the LLM.

    Attributes:
        id: Unique identifier for the parent chunk
        text: Full text content of the parent chunk
        index: Position index within the document
        token_count: Number of tokens in the parent chunk
        embedding: Optional 768-dim embedding vector
        child_indices: List of child chunk indices belonging to this parent
    """

    id: str
    text: str
    index: int
    token_count: int
    embedding: Optional[List[float]] = None
    child_indices: List[int] = field(default_factory=list)


@dataclass
class ProcessingProgress:
    """Tracks progress for long-running processing operations."""

    stage: str
    current: int
    total: int
    message: str
    percent_complete: float = 0.0

    def update(self, current: int, message: str = None):
        """Update progress with new values."""
        self.current = current
        if message:
            self.message = message
        if self.total > 0:
            self.percent_complete = round((current / self.total) * 100, 1)


class GeminiClient:
    """
    Client for Google Gemini API operations.

    Handles embedding generation (text-embedding-004) and entity extraction
    using Gemini's language models.
    """

    def __init__(self, api_key: str = None):
        """
        Initialize Gemini client.

        Args:
            api_key: Google Gemini API key (defaults to GEMINI_API_KEY env var)
        """
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.embedding_model = "text-embedding-004"
        self.extraction_model = "gemini-1.5-pro"
        self._client = None

    async def get_embedding(self, text: str) -> List[float]:
        """
        Generate 768-dimensional embedding for text using Gemini text-embedding-004.

        Args:
            text: Text to generate embedding for

        Returns:
            768-dimensional embedding vector
        """
        try:
            import google.generativeai as genai

            if not self.api_key:
                raise ValueError("GEMINI_API_KEY not configured")

            genai.configure(api_key=self.api_key)

            # Truncate text if too long (embedding model has token limits)
            max_chars = 30000  # Conservative limit for embedding model
            truncated_text = text[:max_chars] if len(text) > max_chars else text

            # Generate embedding using the embedding model
            result = genai.embed_content(
                model=self.embedding_model,
                content=truncated_text,
                task_type="semantic_similarity",
            )

            embedding = result.get("embedding", [])
            return embedding

        except ImportError:
            logger.warning("google-generativeai not installed, using mock embedding")
            return self._mock_embedding(text)
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            return self._mock_embedding(text)

    async def get_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts in batch.

        Args:
            texts: List of texts to generate embeddings for

        Returns:
            List of 768-dimensional embedding vectors
        """
        embeddings = []
        for text in texts:
            embedding = await self.get_embedding(text)
            embeddings.append(embedding)
        return embeddings

    async def extract_entities(self, chunk_text: str, chunk_id: str) -> List[Entity]:
        """
        Extract entities from chunk text using Gemini LLM.

        Args:
            chunk_text: Text content to extract entities from
            chunk_id: ID of the chunk for entity linking

        Returns:
            List of extracted Entity objects
        """
        try:
            import google.generativeai as genai

            if not self.api_key:
                raise ValueError("GEMINI_API_KEY not configured")

            genai.configure(api_key=self.api_key)

            # Prompt for entity extraction
            prompt = f"""
            Extract entities from the following academic text. For each entity, identify:
            - Type: Topic, Concept, Methodology, Finding, or Definition
            - Name: The entity name/term
            - Definition: Brief definition or description

            Return as JSON array with this structure:
            [
                {{"type": "Concept", "name": "Entity Name", "definition": "Brief definition"}}
            ]

            Text:
            {chunk_text[:10000]}  # Limit text size for API
            """

            model = genai.GenerativeModel(self.extraction_model)
            response = model.generate_content(prompt)
            response_text = response.text

            # Parse JSON from response
            entities = self._parse_entities_response(response_text, chunk_id)
            return entities

        except ImportError:
            logger.warning("google-generativeai not installed, using mock entities")
            return self._mock_entities(chunk_text, chunk_id)
        except Exception as e:
            logger.error(f"Entity extraction failed: {e}")
            return self._mock_entities(chunk_text, chunk_id)

    def _parse_entities_response(
        self, response_text: str, chunk_id: str
    ) -> List[Entity]:
        """Parse entity extraction response into Entity objects."""
        entities = []

        try:
            # Extract JSON from response (handle markdown code blocks)
            json_text = response_text
            if "```json" in response_text:
                json_text = response_text.split("```json")[1].split("```")[0]
            elif "```" in response_text:
                json_text = response_text.split("```")[1].split("```")[0]

            data = json.loads(json_text.strip())

            for item in data:
                entity_type_str = item.get("type", "Concept")
                try:
                    entity_type = EntityType(entity_type_str.upper())
                except ValueError:
                    entity_type = EntityType.CONCEPT

                entity_id = self._generate_entity_id(
                    item.get("name", "unknown"), chunk_id
                )

                entities.append(
                    Entity(
                        id=entity_id,
                        name=item.get("name", "Unknown"),
                        entity_type=entity_type,
                        definition=item.get("definition", ""),
                    )
                )

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse entity extraction response: {e}")

        return entities

    def _generate_entity_id(self, name: str, chunk_id: str) -> str:
        """Generate unique entity ID based on name and chunk."""
        content = f"{name}:{chunk_id}"
        return f"entity_{hashlib.md5(content.encode()).hexdigest()[:12]}"

    def _mock_embedding(self, text: str) -> List[float]:
        """Generate mock embedding for testing without API access."""
        import numpy as np

        np.random.seed(hash(text) % (2**32))
        return list(np.random.randn(768).astype(np.float64))

    def _mock_entities(self, text: str, chunk_id: str) -> List[Dict[str, Any]]:
        """Generate mock entities for testing without API access."""
        # Extract potential entities from text (simple heuristic)
        entities = []
        words = text.split()[:50]  # Sample words from text

        for word in words:
            if len(word) > 5 and word.isalpha():
                entity_id = self._generate_entity_id(word, chunk_id)
                entities.append(
                    {
                        "id": entity_id,
                        "name": word,
                        "entity_type": EntityType.CONCEPT.value,
                        "definition": f"Extracted from chunk {chunk_id}",
                        "category": "CONCEPT",
                        "confidence": 0.5,
                        "context_snippet": text[:150],
                        "chunk_id": chunk_id,
                    }
                )

        return entities[:5]  # Limit to 5 entities per chunk

    async def generate_text(self, prompt: str, max_tokens: int = 2048) -> str:
        """
        Generate text using Gemini LLM.

        Args:
            prompt: The prompt to send to the model
            max_tokens: Maximum tokens in response

        Returns:
            Generated text response
        """
        try:
            import google.generativeai as genai

            if not self.api_key:
                raise ValueError("GEMINI_API_KEY not configured")

            genai.configure(api_key=self.api_key)

            model = genai.GenerativeModel(self.extraction_model)
            response = model.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(
                    max_output_tokens=max_tokens, temperature=0.2
                ),
            )

            return response.text

        except ImportError:
            logger.warning("google-generativeai not installed")
            return ""
        except Exception as e:
            logger.error(f"Text generation failed: {e}")
            return ""

    def _count_tokens(self, text: str) -> int:
        """
        Count tokens in text using tiktoken.

        Falls back to whitespace-based counting if tiktoken unavailable.

        Args:
            text: Text to count tokens for

        Returns:
            Token count
        """
        try:
            import tiktoken

            encoding = tiktoken.get_encoding("cl100k_base")
            return len(encoding.encode(text))
        except ImportError:
            # Fallback to whitespace tokenization
            return len(text.split())

    def _generate_entity_id(self, prefix: str, text: str) -> str:
        """Generate hash-based entity ID."""
        hash_str = hashlib.md5(text.lower().encode()).hexdigest()[:12]
        clean_prefix = prefix.lower().replace("_", "")
        return f"{clean_prefix}_{hash_str}"

    def _parse_entities_response(
        self, response_text: str, chunk_id: str
    ) -> List[Dict[str, Any]]:
        """
        Parse entity extraction response into structured format.

        Args:
            response_text: Raw LLM response
            chunk_id: ID of source chunk for linking

        Returns:
            List of entity dicts with name, category, definition, confidence, context
        """
        entities = []

        try:
            # Extract JSON from response
            json_text = response_text.strip()

            # Handle markdown code blocks
            if "```json" in response_text:
                json_text = response_text.split("```json")[1].split("```")[0]
            elif "```" in response_text:
                json_text = response_text.split("```")[1].split("```")[0]

            # Find JSON array bounds
            json_text = json_text.strip()
            if not (json_text.startswith("[") and json_text.endswith("]")):
                start = json_text.find("[")
                end = json_text.rfind("]") + 1
                if start >= 0 and end > start:
                    json_text = json_text[start:end]
                else:
                    raise ValueError("No JSON array found")

            data = json.loads(json_text)

            # Parse each entity
            for item in data:
                entity_type_str = item.get("category", "CONCEPT").upper()

                # Map to EntityType
                type_mapping = {
                    "TOPIC": "Topic",
                    "CONCEPT": "Concept",
                    "METHODOLOGY": "Methodology",
                    "FINDING": "Finding",
                }
                entity_type = type_mapping.get(entity_type_str, "Concept")
                prefix = entity_type.lower()

                entity = {
                    "id": self._generate_entity_id(prefix, item.get("name", "")),
                    "name": item.get("name", "Unknown"),
                    "entity_type": entity_type,
                    "definition": item.get("definition", ""),
                    "category": item.get("category", "General"),
                    "confidence": float(item.get("confidence", 0.7)),
                    "context_snippet": (item.get("context_snippet", "") or "")[:150],
                    "chunk_id": chunk_id,
                }

                if entity["name"] and entity["name"] != "Unknown":
                    entities.append(entity)

            logger.debug(f"Parsed {len(entities)} entities from response")

        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"Failed to parse entity response: {e}")

        return entities

    async def extract_entities(
        self, chunk_text: str, chunk_id: str, max_tokens: int = 4096
    ) -> List[Dict[str, Any]]:
        """
        Extract entities from chunk text using Gemini LLM.

        Args:
            chunk_text: Text content to extract entities from
            chunk_id: ID of the chunk for entity linking
            max_tokens: Maximum tokens in response

        Returns:
            List of extracted entity dicts
        """
        try:
            import google.generativeai as genai

            if not self.api_key:
                raise ValueError("GEMINI_API_KEY not configured")

            genai.configure(api_key=self.api_key)

            # Build prompt with entity extraction template
            prompt = ENTITY_EXTRACTION_PROMPT.format(chunk_text=chunk_text[:5000])

            model = genai.GenerativeModel(self.extraction_model)
            response = model.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(
                    max_output_tokens=max_tokens, temperature=0.2
                ),
            )

            response_text = response.text

            if not response_text:
                logger.warning(f"Empty response for chunk {chunk_id}")
                return []

            # Parse entities from response
            entities = self._parse_entities_response(response_text, chunk_id)
            logger.info(f"Extracted {len(entities)} entities from chunk {chunk_id}")

            return entities

        except ImportError:
            logger.warning("google-generativeai not installed")
            return self._mock_entities(chunk_text, chunk_id)
        except Exception as e:
            logger.error(f"Entity extraction failed for chunk {chunk_id}: {e}")
            return self._mock_entities(chunk_text, chunk_id)


class KnowledgeGraphProcessor:
    """
    Core processor for converting documents to knowledge graphs.

    Orchestrates the complete pipeline:
    1. Document loading and parsing (PDF/TXT)
    2. Semantic chunking with overlap
    3. Embedding generation (768-dim via Gemini)
    4. Entity extraction (Gemini LLM)
    5. Neo4j storage with module_id tagging
    6. Progress tracking and error handling

    All nodes created include module_id for filtering and isolation.

    Chunking Strategies (from AURA-CHAT/backend):
    - LLM-based semantic chunking: Uses Gemini to identify topic boundaries
    - Sentence-based fallback: Splits at sentence boundaries with overlap
    - Fixed-size fallback: Token-based with configurable overlap
    """

    def __init__(
        self,
        driver=None,
        gemini_client: GeminiClient = None,
        chunk_size: int = 800,
        chunk_overlap: int = 100,
        min_chunk_tokens: int = 500,
        max_chunk_tokens: int = 1000,
    ):
        """
        Initialize the Knowledge Graph Processor.

        Args:
            driver: Neo4j driver instance (defaults to neo4j_config.neo4j_driver)
            gemini_client: GeminiClient instance (created if not provided)
            chunk_size: Target token size for text chunks (default: 800)
            chunk_overlap: Token overlap between chunks (default: 100)
            min_chunk_tokens: Minimum tokens per chunk (default: 500)
            max_chunk_tokens: Maximum tokens per chunk (default: 1000)
        """
        self.driver = driver or neo4j_driver
        self.gemini = gemini_client or GeminiClient()
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_tokens = min_chunk_tokens
        self.max_chunk_tokens = max_chunk_tokens

        # Initialize tiktoken for accurate token counting
        self._init_tokenizer()

        # Progress callback storage
        self._progress_callback: Optional[Callable[[ProcessingProgress], None]] = None

        logger.info(
            f"KnowledgeGraphProcessor initialized: "
            f"chunk_size={chunk_size}, overlap={chunk_overlap}, "
            f"min_tokens={min_chunk_tokens}, max_tokens={max_chunk_tokens}"
        )

    def _init_tokenizer(self):
        """Initialize tiktoken encoder for accurate token counting."""
        try:
            import tiktoken

            self.encoding = tiktoken.get_encoding("cl100k_base")
        except ImportError:
            logger.warning("tiktoken not available, using whitespace tokenization")
            self.encoding = None

    def set_progress_callback(self, callback: Callable[[ProcessingProgress], None]):
        """
        Set callback for progress updates during processing.

        Args:
            callback: Function to call with ProcessingProgress updates
        """
        self._progress_callback = callback

    def _emit_progress(self, stage: str, current: int, total: int, message: str):
        """Emit progress update via callback."""
        progress = ProcessingProgress(
            stage=stage, current=current, total=total, message=message
        )
        if self._progress_callback:
            self._progress_callback(progress)
        logger.debug(f"Progress [{stage}]: {current}/{total} - {message}")

    async def process_document(
        self,
        document_id: str,
        module_id: str,
        user_id: str,
        file_path: str = None,
        document_data: Dict[str, Any] = None,
        use_hierarchical_chunking: bool = False,
        use_llm_extraction: bool = True,
        generate_entity_embeddings: bool = True,
        enable_semantic_dedup: bool = True,
        template_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Process a single document into a knowledge graph.

        Args:
            document_id: Unique identifier for the document
            module_id: Module ID for tagging all created nodes
            user_id: User who owns this document
            file_path: Path to the document file (PDF/TXT)
            document_data: Pre-loaded document data (alternative to file_path)
            use_hierarchical_chunking: If True, use parent-child chunking strategy
                for improved RAG retrieval. Parent chunks (~1500 tokens) provide
                section-level context, child chunks (~800 tokens) for precise search.
            use_llm_extraction: If True, use LLMEntityExtractor for entity extraction.
                This provides better extraction quality with confidence scoring.
                Falls back to GeminiClient extraction if LLM extraction fails.
            generate_entity_embeddings: If True, generate 768-dim embeddings for
                all extracted entities and store them in Neo4j. This enables
                semantic search over entities. Default: True.
            enable_semantic_dedup: If True, deduplicate entities using semantic
                similarity (0.85 cosine threshold) on embeddings. Reduces duplicates
                like "ML" and "Machine Learning". Default: True.
            template_id: If provided, use template-based extraction. Values:
                - None: Use legacy extraction (default)
                - "auto": Auto-detect template from content
                - Template ID (e.g., "lecture_notes"): Use specific template

        Returns:
            Dict containing processing summary:
            - document_id: The processed document ID
            - chunk_count: Number of chunks created
            - entity_count: Number of entities extracted
            - entities_deduplicated: Number of entities after deduplication
            - parent_chunk_count: Number of parent chunks (if hierarchical)
            - extraction_method: 'llm', 'template', or 'basic'
            - template_id: Template ID used (if template extraction)
            - template_confidence: Template detection confidence (if auto-detected)
            - entities_embedded: Number of entities with embeddings (if generated)
            - status: 'success' or 'error'
            - error: Error message if failed
        """
        result = {
            "document_id": document_id,
            "module_id": module_id,
            "chunk_count": 0,
            "entity_count": 0,
            "entities_deduplicated": 0,
            "parent_chunk_count": 0,
            "extraction_method": "basic",
            "template_id": None,
            "template_confidence": None,
            "entities_embedded": 0,
            "status": "processing",
            "error": None,
        }

        # Store extraction mode for use in _extract_entities
        self._use_llm_extraction = use_llm_extraction
        self._generate_entity_embeddings = generate_entity_embeddings

        # Initialize LLM extractor if using LLM extraction
        if use_llm_extraction:
            try:
                self._llm_extractor = LLMEntityExtractor(api_key=self.gemini.api_key)
                result["extraction_method"] = "llm"
            except Exception as e:
                logger.warning(
                    f"Failed to initialize LLMEntityExtractor, falling back to basic: {e}"
                )
                self._llm_extractor = None
                self._use_llm_extraction = False
        else:
            self._llm_extractor = None

        # Initialize template extractor if template_id is provided (11-03-PLAN)
        self._template_extractor = None
        self._template = None
        if template_id:
            try:
                registry = get_template_registry()
                
                if template_id == "auto":
                    # Auto-detect template will be done after loading content
                    self._template_extractor = get_template_extractor(self._llm_extractor)
                    result["extraction_method"] = "template"
                    logger.info("Template auto-detection enabled")
                else:
                    # Use specific template
                    self._template = registry.get(template_id)
                    if self._template:
                        self._template_extractor = get_template_extractor(self._llm_extractor)
                        result["extraction_method"] = "template"
                        result["template_id"] = template_id
                        logger.info(f"Using extraction template: {template_id}")
                    else:
                        logger.warning(f"Template not found: {template_id}, using legacy extraction")
            except Exception as e:
                logger.warning(f"Failed to initialize template extractor: {e}")

        try:
            self._emit_progress("loading", 0, 1, f"Loading document {document_id}")

            # Step 1: Load document content
            text = await self._parse_document(document_id, file_path, document_data)
            if not text:
                raise ValueError(f"Failed to load document content: {document_id}")

            result["text_length"] = len(text)

            # Auto-detect template if requested (11-03-PLAN)
            if template_id == "auto" and text:
                try:
                    registry = get_template_registry()
                    template, confidence = registry.detect_template(text)
                    self._template = template
                    result["template_id"] = template.id
                    result["template_confidence"] = float(confidence)
                    logger.info(f"Auto-detected template: {template.id} (confidence: {confidence:.2f})")
                except Exception as e:
                    logger.warning(f"Template auto-detection failed: {e}")

            # Step 2: Create chunks (hierarchical or flat)
            if use_hierarchical_chunking:
                self._emit_progress(
                    "chunking",
                    0,
                    1,
                    f"Creating hierarchical chunks from {len(text)} chars",
                )

                # Use hierarchical parent-child chunking
                hierarchical_result = await self.chunk_text_hierarchical(
                    text, document_id, module_id
                )
                parent_chunks = hierarchical_result["parent_chunks"]
                child_chunks_data = hierarchical_result["child_chunks"]
                relationships = hierarchical_result["relationships"]

                result["parent_chunk_count"] = len(parent_chunks)
                result["chunk_count"] = len(child_chunks_data)

                # Convert child chunk dicts to Chunk objects
                chunks = []
                for child_data in child_chunks_data:
                    chunk = Chunk(
                        id=f"chunk_{document_id}_{child_data['index']}",
                        text=child_data["text"],
                        index=child_data["index"],
                        token_count=child_data["token_count"],
                    )
                    chunks.append(chunk)

                self._emit_progress(
                    "embeddings",
                    0,
                    len(chunks),
                    f"Generating embeddings for {len(chunks)} child chunks",
                )
            else:
                self._emit_progress(
                    "chunking", 0, 1, f"Creating chunks from {len(text)} chars"
                )

                # Use flat chunking (original behavior)
                chunks = await self._create_chunks(text, document_id, module_id)
                parent_chunks = None
                relationships = None

            result["chunk_count"] = len(chunks)
            self._emit_progress("embeddings", 0, len(chunks), "Generating embeddings")

            # Step 3: Generate embeddings for chunks
            if chunks:
                embeddings = await self._generate_embeddings([c.text for c in chunks])
                for chunk, embedding in zip(chunks, embeddings):
                    chunk.embedding = embedding

            self._emit_progress("entities", 0, len(chunks), "Extracting entities")

            # Step 4: Extract entities
            all_entities = []
            
            # Use template-based extraction if available (11-03-PLAN)
            if self._template_extractor and self._template:
                self._emit_progress(
                    "entities", 
                    0, 
                    1, 
                    f"Extracting entities using template: {self._template.name}"
                )
                try:
                    # Import EntityType for mapping
                    # (Assuming it's available in scope, otherwise standard string fallback works)
                    
                    extraction_result = self._template_extractor.extract_with_template(
                        text, 
                        template_id=self._template.id
                    )
                    
                    # Convert dicts to Entity objects
                    for item in extraction_result.entities:
                        try:
                            # Map entity type
                            entity_type_str = item.get("type", "Concept").upper()
                            try:
                                entity_type = EntityType(entity_type_str)
                            except ValueError:
                                # Try title case fallback or default
                                try:
                                    entity_type = EntityType(item.get("type", "Concept").title())
                                except ValueError:
                                    entity_type = EntityType.CONCEPT
                            
                            # Generate ID (use module_id as scope + name hash)
                            entity_id = self._generate_entity_id(
                                item.get("name", "unknown"), module_id
                            )
                            
                            entities_props = {
                                "confidence": item.get("confidence", 0.7),
                                "category": item.get("type", "Concept"),
                                "context_snippet": item.get("source_section", "")[:150],
                                "template_section": item.get("source_section", "")
                            }
                            
                            all_entities.append(
                                Entity(
                                    id=entity_id,
                                    name=item.get("name", "Unknown"),
                                    entity_type=entity_type,
                                    definition=item.get("definition", ""),
                                    properties=entities_props
                                )
                            )
                        except Exception as e:
                            logger.warning(f"Failed to convert template entity: {e}")
                            
                    result["quality_score"] = extraction_result.quality_score
                    logger.info(f"Template extraction found {len(all_entities)} entities")
                    
                    # Handle relationships from template if any
                    # (We'll store them in entity_relationships later if format matches)
                    # For now just use the entities
                    
                except Exception as e:
                    logger.error(f"Template extraction failed: {e}")
                    # Fallback to standard extraction is complex here as we moved past it
                    # But we can leave all_entities empty and let it proceed (or fail gracefully)

            # Fallback to chunk-based extraction if no template or empty results
            if not all_entities:
                if self._template:
                    logger.warning("Template extraction yielded no entities, falling back to chunk-based")
                
                for i, chunk in enumerate(chunks):
                    entities = await self._extract_entities(chunk)
                    chunk.entities = entities
                    all_entities.extend(entities)
                    self._emit_progress(
                        "entities",
                        i + 1,
                        len(chunks),
                        f"Extracted {len(entities)} entities from chunk {i + 1}",
                    )

            result["entity_count"] = len(all_entities)

            # Step 4.5: Extract entity-entity relationships using LLM
            entity_relationships: List[EntityRelationship] = []
            if (
                getattr(self, "_use_llm_extraction", False)
                and getattr(self, "_llm_extractor", None)
                and len(all_entities) >= 2
            ):
                self._emit_progress(
                    "relationships",
                    0,
                    1,
                    f"Extracting entity relationships from {len(all_entities)} entities",
                )
                try:
                    # Prepare entities dict for relationship extraction
                    entities_dict = self._prepare_entities_for_relationship_extraction(
                        all_entities
                    )
                    entity_relationships = (
                        await self._llm_extractor.extract_relationships(
                            text, entities_dict, document_id
                        )
                    )
                    result["relationship_count"] = len(entity_relationships)
                    logger.info(
                        f"Extracted {len(entity_relationships)} entity-entity relationships"
                    )
                except Exception as e:
                    logger.warning(f"Entity relationship extraction failed: {e}")
                    entity_relationships = []

            self._emit_progress("storing", 0, 1, "Storing in Neo4j")

            # Step 4.7: Semantic deduplication of entities (09-06-PLAN)
            dedup_mapping = {}  # Maps old entity name -> canonical name
            if enable_semantic_dedup and len(all_entities) >= 3:
                self._emit_progress(
                    "deduplication",
                    0,
                    1,
                    f"Deduplicating {len(all_entities)} entities semantically",
                )
                try:
                    # Generate embeddings for deduplication
                    embedding_service = EmbeddingService(api_key=self.gemini.api_key)
                    entity_embeddings = {}
                    entity_names = [
                        e.get("name", "")
                        if isinstance(e, dict)
                        else getattr(e, "name", "")
                        for e in all_entities
                    ]
                    embeddings_list = embedding_service.embed_batch(entity_names)
                    for name, emb in zip(entity_names, embeddings_list):
                        if emb:  # Only add if embedding was generated
                            entity_embeddings[name] = emb

                    # Run deduplication
                    if entity_embeddings:
                        deduplicator = EntityDeduplicator(
                            similarity_threshold=ENTITY_DEDUP_SIMILARITY_THRESHOLD
                        )
                        # Convert all_entities to list of dicts if needed
                        entities_as_dicts = []
                        for e in all_entities:
                            if isinstance(e, dict):
                                entity_dict = dict(e)
                                entity_dict["_entity_obj"] = e
                                entities_as_dicts.append(entity_dict)
                                continue

                            entity_properties = dict(getattr(e, "properties", {}) or {})
                            entities_as_dicts.append(
                                {
                                    "name": e.name,
                                    "id": e.id,
                                    "entity_type": e.entity_type.value,
                                    "definition": e.definition,
                                    "properties": entity_properties,
                                    "confidence_score": entity_properties.get(
                                        "confidence", 0.7
                                    ),
                                    "_entity_obj": e,
                                }
                            )
                        (
                            deduplicated_entities,
                            dedup_mapping,
                        ) = deduplicator.deduplicate(
                            entities_as_dicts, entity_embeddings
                        )

                        original_count = len(all_entities)
                        deduped_count = len(deduplicated_entities)
                        reduction_pct = (
                            ((original_count - deduped_count) / original_count * 100)
                            if original_count > 0
                            else 0
                        )

                        result["entities_deduplicated"] = deduped_count
                        result["dedup_reduction_percent"] = round(reduction_pct, 1)
                        result["dedup_mappings"] = dedup_mapping

                        # Update all_entities with deduplicated list
                        rebuilt_entities = []
                        for entity_dict in deduplicated_entities:
                            entity_obj = entity_dict.get("_entity_obj")
                            if isinstance(entity_obj, Entity):
                                entity_obj.name = entity_dict.get(
                                    "name", entity_obj.name
                                )
                                entity_obj.definition = entity_dict.get(
                                    "definition", entity_obj.definition
                                )
                                entity_type_value = entity_dict.get("entity_type")
                                if entity_type_value:
                                    try:
                                        entity_obj.entity_type = EntityType(
                                            entity_type_value
                                        )
                                    except ValueError:
                                        try:
                                            entity_obj.entity_type = EntityType(
                                                entity_type_value.title()
                                            )
                                        except ValueError:
                                            entity_obj.entity_type = (
                                                entity_obj.entity_type
                                            )
                                entity_properties = dict(entity_obj.properties or {})
                                entity_properties.update(
                                    entity_dict.get("properties", {}) or {}
                                )
                                for key in [
                                    "category",
                                    "confidence",
                                    "context_snippet",
                                ]:
                                    if key in entity_dict:
                                        entity_properties[key] = entity_dict[key]
                                entity_obj.properties = entity_properties
                                rebuilt_entities.append(entity_obj)
                                continue

                            entity_type_value = entity_dict.get(
                                "entity_type", "Concept"
                            )
                            try:
                                entity_type = EntityType(entity_type_value)
                            except ValueError:
                                try:
                                    entity_type = EntityType(entity_type_value.title())
                                except ValueError:
                                    entity_type = EntityType.CONCEPT
                            entity_properties = dict(
                                entity_dict.get("properties", {}) or {}
                            )
                            for key in ["category", "confidence", "context_snippet"]:
                                if key in entity_dict:
                                    entity_properties[key] = entity_dict[key]
                            rebuilt_entities.append(
                                Entity(
                                    id=entity_dict.get("id", ""),
                                    name=entity_dict.get("name", ""),
                                    entity_type=entity_type,
                                    definition=entity_dict.get("definition", ""),
                                    properties=entity_properties,
                                )
                            )

                        all_entities = rebuilt_entities

                        # Update chunk.entities to point to canonical entities
                        if dedup_mapping:
                            canonical_by_name = {
                                entity.name: entity for entity in all_entities
                            }
                            for chunk in chunks:
                                if hasattr(chunk, "entities"):
                                    updated_entities = []
                                    seen_ids = set()
                                    for entity in chunk.entities:
                                        entity_name = (
                                            entity.get("name", "")
                                            if isinstance(entity, dict)
                                            else getattr(entity, "name", "")
                                        )
                                        canonical_name = dedup_mapping.get(
                                            entity_name, entity_name
                                        )
                                        canonical_entity = canonical_by_name.get(
                                            canonical_name
                                        )
                                        if not canonical_entity:
                                            if isinstance(entity, Entity):
                                                canonical_entity = entity
                                            else:
                                                continue
                                        if canonical_entity.id in seen_ids:
                                            continue
                                        seen_ids.add(canonical_entity.id)
                                        updated_entities.append(canonical_entity)
                                    chunk.entities = updated_entities

                        logger.info(
                            f"Semantic deduplication: {original_count} -> {deduped_count} entities "
                            f"({reduction_pct:.1f}% reduction)"
                        )
                    else:
                        logger.warning(
                            "No embeddings generated for deduplication, skipping"
                        )
                        result["entities_deduplicated"] = len(all_entities)
                except Exception as e:
                    logger.warning(f"Semantic deduplication failed: {e}")
                    result["entities_deduplicated"] = len(all_entities)
            else:
                result["entities_deduplicated"] = len(all_entities)

            # Step 5: Store everything in Neo4j with module_id tagging
            await self._store_in_neo4j(
                document_id, module_id, user_id, chunks, all_entities
            )

            # Step 5.5: Store entity-entity relationships
            if entity_relationships:
                self._emit_progress(
                    "storing_relationships",
                    0,
                    1,
                    f"Storing {len(entity_relationships)} entity relationships",
                )
                await self._store_entity_relationships(
                    entity_relationships, module_id, all_entities
                )

            # Step 6: Store parent chunks and relationships (if hierarchical)
            if use_hierarchical_chunking and parent_chunks:
                self._emit_progress(
                    "storing_parents",
                    0,
                    1,
                    f"Storing {len(parent_chunks)} parent chunks",
                )
                await self._store_parent_chunks(
                    parent_chunks, document_id, module_id, user_id
                )

                # Link child chunks to parent chunks
                if relationships:
                    with self.driver.session() as session:
                        for rel in relationships:
                            parent_id = (
                                f"parent_chunk_{document_id}_{rel['parent_index']}"
                            )
                            child_id = f"chunk_{document_id}_{rel['child_index']}"
                            await self._link_child_to_parent(
                                session, child_id, parent_id
                            )

            # Step 7: Generate and store entity embeddings
            if getattr(self, "_generate_entity_embeddings", True) and all_entities:
                self._emit_progress(
                    "entity_embeddings",
                    0,
                    1,
                    f"Generating embeddings for {len(all_entities)} entities",
                )
                try:
                    entities_embedded = (
                        await self._generate_and_store_entity_embeddings(
                            all_entities, module_id
                        )
                    )
                    result["entities_embedded"] = entities_embedded
                    logger.info(
                        f"Generated embeddings for {entities_embedded} entities"
                    )
                except Exception as e:
                    logger.warning(f"Entity embedding generation failed: {e}")
                    result["entities_embedded"] = 0

            result["status"] = "success"
            self._emit_progress(
                "complete", 1, 1, f"Processed {document_id} successfully"
            )

            if use_hierarchical_chunking:
                logger.info(
                    f"Document {document_id} processed (hierarchical): "
                    f"{len(parent_chunks)} parents, {len(chunks)} children, "
                    f"{len(all_entities)} entities"
                )
            else:
                logger.info(
                    f"Document {document_id} processed: {len(chunks)} chunks, "
                    f"{len(all_entities)} entities"
                )

        except Exception as e:
            logger.error(f"Document processing failed for {document_id}: {e}")
            result["status"] = "error"
            result["error"] = str(e)
            self._emit_progress("error", 0, 1, f"Processing failed: {e}")

        return result

    async def process_batch(
        self,
        document_ids: List[str],
        module_id: str,
        user_id: str,
        document_map: Dict[str, Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Process multiple documents in batch.

        Args:
            document_ids: List of document IDs to process
            module_id: Module ID for tagging all created nodes
            user_id: User who owns these documents
            document_map: Optional dict mapping document_id to document data

        Returns:
            List of processing results for each document
        """
        results = []

        # Prepare document data map
        doc_map = document_map or {}

        total = len(document_ids)
        for i, doc_id in enumerate(document_ids):
            self._emit_progress(
                "batch", i + 1, total, f"Processing document {i + 1}/{total}: {doc_id}"
            )

            doc_data = doc_map.get(doc_id)
            result = await self.process_document(
                doc_id, module_id, user_id, document_data=doc_data
            )
            results.append(result)

        logger.info(f"Batch processing complete: {len(results)} documents")
        return results

    async def _parse_document(
        self,
        document_id: str,
        file_path: str = None,
        document_data: Dict[str, Any] = None,
    ) -> str:
        """
        Extract text from PDF or plain text file.

        Args:
            document_id: Document identifier
            file_path: Path to the file (optional)
            document_data: Pre-loaded document data with 'content' field (optional)

        Returns:
            Extracted text content
        """
        # If document_data is provided with content, use it
        if document_data and document_data.get("content"):
            return document_data["content"]

        # If file_path is provided, parse the file
        if file_path:
            return await self._parse_file(file_path)

        # Try to find file based on document_id
        # Check common locations
        possible_paths = [
            f"uploads/{document_id}.pdf",
            f"uploads/{document_id}.docx",
            f"uploads/{document_id}.txt",
            f"documents/{document_id}.pdf",
            f"documents/{document_id}.docx",
            f"documents/{document_id}.txt",
        ]

        for path in possible_paths:
            if os.path.exists(path):
                return await self._parse_file(path)

        # Try Firestore if available
        try:
            from config import db

            # Find note in nested subcollections (modules/{id}/notes/{id})
            notes = list(
                db.collection_group("notes")
                .where("__name__", ">=", document_id)
                .where("__name__", "<=", document_id + "\uf8ff")
                .limit(1)
                .stream()
            )
            if notes:
                doc_data = notes[0].to_dict()
                # Return content field if present (some notes store parsed content)
                return doc_data.get("content", "")
        except Exception as e:
            logger.warning(f"Failed to fetch document from Firestore: {e}")

        raise FileNotFoundError(f"Document not found: {document_id}")

    async def _parse_file(self, file_path: str) -> str:
        """
        Parse text from a file (PDF, DOCX, or TXT).

        Args:
            file_path: Path to the file

        Returns:
            Extracted text content
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        file_ext = os.path.splitext(file_path)[1].lower()

        if file_ext == ".pdf":
            return await self._parse_pdf(file_path)
        elif file_ext == ".docx":
            return await self._parse_docx(file_path)
        elif file_ext == ".txt":
            return await self._parse_text(file_path)
        else:
            # Try to detect format from content
            raise ValueError(f"Unsupported file format: {file_ext}")

    async def _parse_pdf(self, file_path: str) -> str:
        """
        Extract text from PDF using PyMuPDF.

        Args:
            file_path: Path to PDF file

        Returns:
            Extracted text content
        """
        try:
            text_parts = []

            doc = fitz.open(file_path)
            for page_num, page in enumerate(doc):
                text = page.get_text()
                if text.strip():
                    text_parts.append(text)

            doc.close()
            return "\n\n".join(text_parts)

        except Exception as e:
            logger.error(f"PDF parsing failed for {file_path}: {e}")
            raise

    async def _parse_docx(self, file_path: str) -> str:
        """
        Extract text from DOCX using DocxParser.

        Args:
            file_path: Path to DOCX file

        Returns:
            Extracted text content including tables

        Raises:
            CorruptedDocxError: If file is corrupted
            PasswordProtectedDocxError: If file is password-protected
            EmptyDocxError: If file has no text content
        """
        try:
            parser = DocxParser()
            result = parser.parse(file_path)

            # Log metadata and structure info
            logger.info(
                f"DOCX parsed: {result.word_count} words, "
                f"{len(result.sections)} sections, "
                f"{len(result.tables)} tables"
            )

            if result.metadata:
                logger.debug(f"DOCX metadata: {result.metadata}")

            return result.text

        except CorruptedDocxError as e:
            logger.error(f"DOCX is corrupted: {file_path} - {e}")
            raise
        except PasswordProtectedDocxError as e:
            logger.error(f"DOCX is password-protected: {file_path} - {e}")
            raise
        except EmptyDocxError as e:
            logger.warning(f"DOCX is empty: {file_path} - {e}")
            raise
        except DocxParseError as e:
            logger.error(f"DOCX parsing failed for {file_path}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error parsing DOCX {file_path}: {e}")
            raise DocxParseError(f"Failed to parse DOCX: {e}") from e

    async def _parse_text(self, file_path: str) -> str:
        """
        Read plain text file.

        Args:
            file_path: Path to text file

        Returns:
            File content as string
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        except UnicodeDecodeError:
            # Try different encodings
            for encoding in ["latin-1", "cp1252", "utf-16"]:
                try:
                    with open(file_path, "r", encoding=encoding) as f:
                        return f.read()
                except UnicodeDecodeError:
                    continue

            raise ValueError(f"Could not decode text file: {file_path}")

    async def _create_chunks(
        self, text: str, document_id: str, module_id: str
    ) -> List[Chunk]:
        """
        Split text into overlapping semantic chunks.

        Uses token-based chunking with overlap to preserve context across chunks.

        Args:
            text: Full text content
            document_id: Document identifier for chunk IDs
            module_id: Module ID for tagging

        Returns:
            List of Chunk objects with text and metadata
        """
        # Simple tokenization (whitespace-based approximation)
        # For production, use a proper tokenizer like tiktoken
        tokens = text.split()
        chunk_count = 0
        chunks = []
        start = 0

        while start < len(tokens):
            # Get chunk tokens
            end = min(start + self.chunk_size, len(tokens))
            chunk_tokens = tokens[start:end]

            # Calculate token count
            token_count = len(chunk_tokens)

            # Create chunk text
            chunk_text = " ".join(chunk_tokens)

            # Generate chunk ID
            chunk_id = f"chunk_{document_id}_{chunk_count}"

            # Create chunk object
            chunk = Chunk(
                id=chunk_id, text=chunk_text, index=chunk_count, token_count=token_count
            )
            chunks.append(chunk)

            chunk_count += 1

            # Move start position with overlap
            start = end - self.chunk_overlap

            # Break if we've reached the end
            if start >= len(tokens):
                break

        logger.info(f"Created {len(chunks)} chunks for document {document_id}")
        return chunks

    async def chunk_text_hierarchical(
        self, text: str, document_id: str, module_id: str
    ) -> Dict[str, Any]:
        """
        Create hierarchical parent-child chunks for improved RAG retrieval.

        Parent chunks: ~1500 tokens (section-level context for LLM)
        Child chunks: ~800 tokens with 200 overlap (for precise search)
        When a child matches, its parent provides expanded context.

        This method is ported from AURA-CHAT/backend/document_processor.py
        to maintain consistency across the AURA monorepo.

        Args:
            text: Full document text
            document_id: Document ID for chunk ID generation
            module_id: Module ID for tagging

        Returns:
            Dict with:
                - 'parent_chunks': List of parent chunk dicts
                - 'child_chunks': List of child chunk dicts
                - 'relationships': List of {parent_index, child_index} mappings
        """
        # Step 1: Normalize text while preserving paragraph structure
        # Don't use normalize_text() here as it collapses newlines to spaces
        # Instead, do lighter normalization that keeps paragraph breaks
        normalized_text = unicodedata.normalize("NFKC", text)
        # Replace various unicode whitespace with regular space (but keep \n)
        normalized_text = re.sub(
            r"[\u00a0\u2000-\u200b\u2028\u2029\u202f\u205f\u3000]", " ", normalized_text
        )
        # Remove control characters except newlines and tabs
        normalized_text = re.sub(
            r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", normalized_text
        )
        # Collapse multiple spaces to single (but keep newlines)
        normalized_text = re.sub(r" +", " ", normalized_text)
        normalized_text = normalized_text.strip()

        total_tokens = count_tokens(normalized_text)
        logger.info(f"Hierarchical chunking: {total_tokens} tokens total")

        parent_chunks = []
        child_chunks = []
        relationships = []

        # Step 2: Create parent chunks by grouping paragraphs
        paragraphs = [p.strip() for p in normalized_text.split("\n") if p.strip()]

        # If normalization collapsed newlines, try splitting on double spaces
        if len(paragraphs) <= 1 and normalized_text:
            # Try sentence-based splitting as fallback
            paragraphs = split_into_sentences(normalized_text)

        current_tokens = 0
        current_text = []
        parent_index = 0

        for paragraph in paragraphs:
            para_tokens = count_tokens(paragraph)

            if current_tokens + para_tokens > PARENT_CHUNK_SIZE:
                if current_text:
                    parent_text = " ".join(current_text)
                    parent_chunks.append(
                        {
                            "index": parent_index,
                            "text": parent_text,
                            "token_count": current_tokens,
                            "type": "parent",
                        }
                    )
                    parent_index += 1

                # Keep some overlap for context continuity
                overlap_paragraphs = []
                overlap_token_count = 0
                parent_overlap = min(200, PARENT_CHUNK_SIZE // 5)

                for prev_para in reversed(current_text):
                    prev_tokens = count_tokens(prev_para)
                    if overlap_token_count + prev_tokens > parent_overlap:
                        break
                    overlap_paragraphs.insert(0, prev_para)
                    overlap_token_count += prev_tokens

                current_text = overlap_paragraphs
                current_tokens = overlap_token_count

            current_text.append(paragraph)
            current_tokens += para_tokens

        # Add final parent chunk
        if current_text:
            parent_text = " ".join(current_text)
            parent_chunks.append(
                {
                    "index": parent_index,
                    "text": parent_text,
                    "token_count": current_tokens,
                    "type": "parent",
                }
            )

        logger.info(f"Created {len(parent_chunks)} parent chunks")

        # Step 3: Create child chunks within each parent using sentence-aware splitting
        child_index = 0
        for parent in parent_chunks:
            parent_text = parent["text"]
            parent_id = parent["index"]

            # Split parent into sentences for cleaner chunk boundaries
            sentences = split_into_sentences(parent_text)
            temp_tokens = 0
            temp_sentences = []

            for sentence in sentences:
                sentence_tokens = count_tokens(sentence)

                # Check if adding this sentence exceeds chunk size
                if temp_tokens + sentence_tokens > CHILD_CHUNK_SIZE:
                    # Create chunk from accumulated sentences
                    if temp_sentences:
                        chunk_text = " ".join(temp_sentences)
                        child_chunks.append(
                            {
                                "index": child_index,
                                "text": chunk_text,
                                "token_count": temp_tokens,
                                "parent_index": parent_id,
                                "type": "child",
                            }
                        )
                        relationships.append(
                            {"parent_index": parent_id, "child_index": child_index}
                        )
                        child_index += 1

                        # Keep overlap for context continuity
                        overlap_sentences = []
                        overlap_token_count = 0
                        for prev_sent in reversed(temp_sentences):
                            prev_tokens = count_tokens(prev_sent)
                            if overlap_token_count + prev_tokens > CHILD_CHUNK_OVERLAP:
                                break
                            overlap_sentences.insert(0, prev_sent)
                            overlap_token_count += prev_tokens

                        temp_sentences = overlap_sentences
                        temp_tokens = overlap_token_count

                    # Handle oversized sentence (fallback to word-by-word)
                    if sentence_tokens > CHILD_CHUNK_SIZE:
                        words = sentence.split()
                        word_temp = []
                        word_tokens_temp = 0

                        for word in words:
                            word_tokens = count_tokens(word + " ")
                            if word_tokens_temp + word_tokens > CHILD_CHUNK_SIZE:
                                if word_temp:
                                    chunk_text = " ".join(word_temp)
                                    child_chunks.append(
                                        {
                                            "index": child_index,
                                            "text": chunk_text,
                                            "token_count": word_tokens_temp,
                                            "parent_index": parent_id,
                                            "type": "child",
                                        }
                                    )
                                    relationships.append(
                                        {
                                            "parent_index": parent_id,
                                            "child_index": child_index,
                                        }
                                    )
                                    child_index += 1
                                word_temp = [word]
                                word_tokens_temp = word_tokens
                            else:
                                word_temp.append(word)
                                word_tokens_temp += word_tokens

                        # Add remaining words to temp for next iteration
                        if word_temp:
                            temp_sentences = [" ".join(word_temp)]
                            temp_tokens = word_tokens_temp
                    else:
                        # Sentence fits after creating chunk, add to fresh temp
                        temp_sentences.append(sentence)
                        temp_tokens += sentence_tokens
                else:
                    # Sentence fits in current chunk, add it
                    temp_sentences.append(sentence)
                    temp_tokens += sentence_tokens

            # Handle final chunk for this parent (with merge logic for small chunks)
            if temp_sentences:
                chunk_text = " ".join(temp_sentences)
                token_count = temp_tokens

                # Check if final chunk is too small (< 50% of target)
                if token_count < CHILD_CHUNK_SIZE * 0.5 and child_chunks:
                    # Only merge if previous chunk belongs to same parent
                    prev_chunk = child_chunks[-1]
                    if prev_chunk.get("parent_index") == parent_id:
                        # Merge with previous chunk
                        prev_chunk["text"] += " " + chunk_text
                        prev_chunk["token_count"] = count_tokens(prev_chunk["text"])
                        logger.debug(
                            f"Merged small final chunk ({token_count} tokens) with previous"
                        )
                    else:
                        # Different parent, keep separate
                        child_chunks.append(
                            {
                                "index": child_index,
                                "text": chunk_text,
                                "token_count": token_count,
                                "parent_index": parent_id,
                                "type": "child",
                            }
                        )
                        relationships.append(
                            {"parent_index": parent_id, "child_index": child_index}
                        )
                        child_index += 1
                else:
                    # Normal size, add as new chunk
                    child_chunks.append(
                        {
                            "index": child_index,
                            "text": chunk_text,
                            "token_count": token_count,
                            "parent_index": parent_id,
                            "type": "child",
                        }
                    )
                    relationships.append(
                        {"parent_index": parent_id, "child_index": child_index}
                    )
                    child_index += 1

        logger.info(
            f"Created {len(child_chunks)} child chunks with "
            f"{len(relationships)} parent-child relationships"
        )

        # Step 4: Add default fields to child chunks for compatibility
        for chunk in child_chunks:
            chunk.setdefault("entities", [])
            chunk.setdefault("entity_names", [])
            chunk.setdefault("primary_entity", "")
            if "position" not in chunk:
                chunk["position"] = {
                    "start": 0,
                    "end": len(chunk.get("text", "")),
                }

        return {
            "parent_chunks": parent_chunks,
            "child_chunks": child_chunks,
            "relationships": relationships,
        }

    async def _store_parent_chunks(
        self,
        parent_chunks: List[Dict[str, Any]],
        document_id: str,
        module_id: str,
        user_id: str,
    ) -> None:
        """
        Store parent chunks in Neo4j with HAS_PARENT_CHUNK relationship.

        Creates ParentChunk nodes and links them to the Document node.
        Also generates embeddings for parent chunks if not already present.

        Args:
            parent_chunks: List of parent chunk dicts from chunk_text_hierarchical
            document_id: Document ID for relationship linking
            module_id: Module ID for tagging all nodes
            user_id: User who owns the document
        """
        if not self.driver:
            raise ValueError("Neo4j driver not available")

        # Generate embeddings for parent chunks if needed
        parent_texts = [p["text"] for p in parent_chunks]
        embeddings = await self._generate_embeddings(parent_texts)

        for parent, embedding in zip(parent_chunks, embeddings):
            parent["embedding"] = embedding

        with self.driver.session() as session:
            for parent in parent_chunks:
                parent_id = f"parent_chunk_{document_id}_{parent['index']}"

                # Create ParentChunk node
                query = """
                MERGE (pc:ParentChunk {id: $id})
                SET pc.text = $text,
                    pc.token_count = $token_count,
                    pc.index = $index,
                    pc.module_id = $module_id,
                    pc.document_id = $document_id,
                    pc.embedding = $embedding
                RETURN pc.id
                """
                session.run(
                    query,
                    {
                        "id": parent_id,
                        "text": parent["text"][:10000],  # Limit text size for Neo4j
                        "token_count": parent["token_count"],
                        "index": parent["index"],
                        "module_id": module_id,
                        "document_id": document_id,
                        "embedding": parent.get("embedding"),
                    },
                )

                # Create HAS_PARENT_CHUNK relationship from Document
                rel_query = """
                MATCH (d:Document {id: $doc_id})
                MATCH (pc:ParentChunk {id: $parent_id})
                MERGE (d)-[r:HAS_PARENT_CHUNK]->(pc)
                RETURN r
                """
                session.run(rel_query, {"doc_id": document_id, "parent_id": parent_id})

        logger.info(
            f"Stored {len(parent_chunks)} parent chunks for document {document_id}"
        )

    async def _link_child_to_parent(
        self, session, child_chunk_id: str, parent_chunk_id: str
    ) -> None:
        """
        Create BELONGS_TO_PARENT relationship between child and parent chunk.

        Args:
            session: Neo4j session
            child_chunk_id: Child chunk ID
            parent_chunk_id: Parent chunk ID
        """
        query = """
        MATCH (c:Chunk {id: $child_id})
        MATCH (pc:ParentChunk {id: $parent_id})
        MERGE (c)-[r:BELONGS_TO_PARENT]->(pc)
        RETURN r
        """
        session.run(query, {"child_id": child_chunk_id, "parent_id": parent_chunk_id})

    async def create_semantic_chunks(
        self, text: str, document_id: str, module_id: str, use_llm: bool = True
    ) -> List[Chunk]:
        """
        Create semantically coherent chunks using LLM.

        Attempts to split document at natural topic boundaries using Gemini.
        Falls back to sentence-based chunking if LLM fails or is unavailable.

        Args:
            text: Full text content
            document_id: Document identifier for chunk IDs
            module_id: Module ID for tagging
            use_llm: Whether to use LLM for semantic splitting (default: True)

        Returns:
            List of Chunk objects with text, metadata, and descriptions
        """
        self._emit_progress("semantic_chunking", 0, 1, "Analyzing document structure")

        # Step 1: Try LLM-based semantic splitting
        if use_llm:
            try:
                semantic_chunks = await self._create_chunks_with_llm(text, document_id)
                if semantic_chunks:
                    # Step 2: Add overlap to each chunk
                    final_chunks = self._add_overlap_to_chunks(
                        semantic_chunks, document_id, module_id
                    )
                    self._emit_progress(
                        "semantic_chunking",
                        1,
                        1,
                        f"Created {len(final_chunks)} semantic chunks",
                    )
                    return final_chunks
            except Exception as e:
                logger.warning(f"LLM-based chunking failed, falling back: {e}")

        # Step 3: Fallback to sentence-based chunking
        self._emit_progress(
            "semantic_chunking", 0, 1, "Using sentence-based chunking fallback"
        )
        fallback_chunks = await self._fallback_sentence_chunker(
            text, document_id, module_id
        )
        final_chunks = self._add_overlap_to_chunks(
            fallback_chunks, document_id, module_id
        )

        self._emit_progress(
            "semantic_chunking",
            1,
            1,
            f"Created {len(final_chunks)} chunks via sentence splitting",
        )
        return final_chunks

    async def _create_chunks_with_llm(
        self, text: str, document_id: str
    ) -> List[Dict[str, Any]]:
        """
        Use LLM to identify semantic chunk boundaries.

        Args:
            text: Full text content
            document_id: Document identifier

        Returns:
            List of chunk dicts with content, description, and indices
        """
        # Limit text for LLM context (first 15K chars should capture multiple sections)
        max_chars = 15000
        truncated_text = text[:max_chars] if len(text) > max_chars else text

        # If text is longer, provide a hint about structure
        if len(text) > max_chars:
            truncated_text += f"\n\n[... Document continues with {len(text) - max_chars} more characters ...]"

        prompt = CHUNK_BY_SEMANTIC_SPLIT.format(content=truncated_text)

        # Get LLM response
        response = await self.gemini.generate_text(prompt, max_tokens=4096)

        if not response:
            raise ValueError("Empty response from LLM")

        # Parse JSON response
        chunks_data = self._parse_chunk_response(response)

        if not chunks_data:
            raise ValueError("Failed to parse chunk response")

        logger.info(f"LLM suggested {len(chunks_data)} semantic chunks")
        return chunks_data

    def _parse_chunk_response(self, response_text: str) -> List[Dict[str, Any]]:
        """
        Parse LLM chunk response into structured format.

        Args:
            response_text: Raw LLM response

        Returns:
            List of chunk dicts with chunk_index, content, description
        """
        try:
            # Extract JSON from response
            json_text = response_text.strip()

            # Handle markdown code blocks
            if "```json" in response_text:
                json_text = response_text.split("```json")[1].split("```")[0]
            elif "```" in response_text:
                json_text = response_text.split("```")[1].split("```")[0]

            # Remove any leading/trailing text before/after JSON
            json_text = json_text.strip()
            if json_text.startswith("[") and json_text.endswith("]"):
                # Good, it's clean JSON
                pass
            else:
                # Try to find JSON array
                start = json_text.find("[")
                end = json_text.rfind("]") + 1
                if start >= 0 and end > start:
                    json_text = json_text[start:end]
                else:
                    raise ValueError("No JSON array found in response")

            data = json.loads(json_text)

            # Validate and normalize
            chunks = []
            for item in data:
                chunk = {
                    "chunk_index": item.get("chunk_index", len(chunks)),
                    "content": item.get("content", "").strip(),
                    "description": item.get("description", "").strip(),
                }
                if chunk["content"]:
                    chunks.append(chunk)

            return chunks

        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"Failed to parse chunk response: {e}")
            return []

    def _add_overlap_to_chunks(
        self, chunks_data: List[Dict[str, Any]], document_id: str, module_id: str
    ) -> List[Chunk]:
        """
        Convert chunk data to Chunk objects with overlap.

        Args:
            chunks_data: List of chunk dicts
            document_id: Document identifier
            module_id: Module ID for tagging

        Returns:
            List of Chunk objects ready for embedding
        """
        final_chunks = []
        chunk_count = 0

        pending_content = ""
        pending_description = ""

        for chunk_data in chunks_data:
            content = chunk_data.get("content", "")
            description = chunk_data.get("description", "")

            if pending_content:
                content = f"{pending_content} {content}".strip()
                if pending_description and description:
                    description = f"{pending_description}; {description}"
                elif pending_description:
                    description = pending_description
                pending_content = ""
                pending_description = ""

            token_count = self._count_tokens(content)

            # Validate chunk size
            if token_count < self.min_chunk_tokens:
                logger.debug(
                    f"Chunk {chunk_count} too small ({token_count} tokens), "
                    "merging with next chunk"
                )
                pending_content = content
                pending_description = description
                continue

            if token_count > self.max_chunk_tokens:
                # Split oversized chunks
                sub_chunks = self._split_oversized_chunk(
                    content, chunk_count, document_id, description
                )
                for sub_chunk in sub_chunks:
                    final_chunks.append(sub_chunk)
                    chunk_count += 1
                continue

            # Create chunk ID
            chunk_id = f"chunk_{document_id}_{chunk_count}"

            # Create Chunk object
            chunk = Chunk(
                id=chunk_id, text=content, index=chunk_count, token_count=token_count
            )

            # Store description in properties for later use
            if description:
                chunk.properties["description"] = description

            final_chunks.append(chunk)
            chunk_count += 1

        if pending_content and final_chunks:
            last_chunk = final_chunks[-1]
            merged_text = f"{last_chunk.text} {pending_content}".strip()
            last_chunk.text = merged_text
            last_chunk.token_count = self._count_tokens(merged_text)
            if pending_description:
                previous_description = last_chunk.properties.get("description", "")
                if previous_description:
                    last_chunk.properties["description"] = (
                        f"{previous_description}; {pending_description}"
                    )
                else:
                    last_chunk.properties["description"] = pending_description
        elif pending_content:
            token_count = self._count_tokens(pending_content)
            chunk_id = f"chunk_{document_id}_{chunk_count}"
            chunk = Chunk(
                id=chunk_id,
                text=pending_content,
                index=chunk_count,
                token_count=token_count,
            )
            if pending_description:
                chunk.properties["description"] = pending_description
            final_chunks.append(chunk)

        logger.info(f"Created {len(final_chunks)} validated chunks")
        return final_chunks

    def _split_oversized_chunk(
        self, content: str, base_index: int, document_id: str, description: str
    ) -> List[Chunk]:
        """
        Split oversized chunks into smaller pieces.

        Args:
            content: Chunk content exceeding max_chunk_tokens
            base_index: Base index for chunk IDs
            document_id: Document identifier
            description: Original chunk description

        Returns:
            List of smaller Chunk objects
        """
        chunks = []
        tokens = content.split()
        sub_count = 0

        start = 0
        while start < len(tokens):
            end = min(start + self.chunk_size, len(tokens))
            sub_tokens = tokens[start:end]
            sub_content = " ".join(sub_tokens)

            chunk_id = f"chunk_{document_id}_{base_index}_{sub_count}"
            chunk = Chunk(
                id=chunk_id,
                text=sub_content,
                index=base_index + sub_count,
                token_count=len(sub_tokens),
            )
            chunk.properties["description"] = f"{description} (part {sub_count + 1})"
            chunk.properties["is_split"] = True

            chunks.append(chunk)
            sub_count += 1

            # Move start with overlap
            start = end - self.chunk_overlap

        return chunks

    async def _fallback_sentence_chunker(
        self, text: str, document_id: str, module_id: str
    ) -> List[Dict[str, Any]]:
        """
        Fallback chunking using sentence boundaries.

        Splits text at sentence boundaries and groups sentences into chunks
        targeting CHUNK_SIZE tokens.

        Args:
            text: Full text content
            document_id: Document identifier
            module_id: Module ID for tagging

        Returns:
            List of chunk dicts
        """
        # Split into sentences
        import re

        # Common sentence-ending punctuation
        sentence_endings = re.compile(r"[.!?]\s+")
        sentences = sentence_endings.split(text)

        # Filter empty sentences and clean up
        sentences = [s.strip() for s in sentences if s.strip()]

        # Group sentences into chunks
        chunks = []
        current_chunk = []
        current_tokens = 0
        chunk_index = 0

        for sentence in sentences:
            sentence_tokens = self._count_tokens(sentence)

            # If adding this sentence would exceed max, start new chunk
            if (
                current_tokens + sentence_tokens > self.max_chunk_tokens
                and current_chunk
            ):
                # Finalize current chunk
                content = " ".join(current_chunk)
                chunks.append(
                    {
                        "chunk_index": chunk_index,
                        "content": content,
                        "description": f"Section {chunk_index + 1}",
                    }
                )

                # Start new chunk with overlap
                overlap_start = max(0, len(current_chunk) - 2)  # Keep last 2 sentences
                current_chunk = current_chunk[overlap_start:]
                current_tokens = sum(self._count_tokens(s) for s in current_chunk)
                chunk_index += 1

            current_chunk.append(sentence)
            current_tokens += sentence_tokens

        # Don't forget the last chunk
        if current_chunk:
            content = " ".join(current_chunk)
            chunks.append(
                {
                    "chunk_index": chunk_index,
                    "content": content,
                    "description": f"Section {chunk_index + 1}",
                }
            )

        logger.info(f"Fallback chunker created {len(chunks)} chunks")
        return chunks

    def _count_tokens(self, text: str) -> int:
        """
        Count tokens in text using tiktoken (accurate GPT-4 compatible counting).

        Falls back to whitespace-based counting if tiktoken unavailable.

        Args:
            text: Text to count tokens for

        Returns:
            Token count
        """
        if self.encoding:
            return len(self.encoding.encode(text))
        return len(text.split())

    def _validate_chunk_size(self, chunk: Chunk) -> bool:
        """
        Validate chunk meets size requirements.

        Args:
            chunk: Chunk to validate

        Returns:
            True if chunk size is valid
        """
        return self.min_chunk_tokens <= chunk.token_count <= self.max_chunk_tokens

    async def _generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Generate Gemini embeddings for chunks.

        Args:
            texts: List of text strings to embed

        Returns:
            List of 768-dimensional embedding vectors
        """
        # Process in batches to avoid rate limits
        batch_size = 10
        all_embeddings = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            batch_embeddings = await self.gemini.get_embeddings_batch(batch)
            all_embeddings.extend(batch_embeddings)

            # Small delay between batches to avoid rate limits
            if i + batch_size < len(texts):
                await asyncio.sleep(0.1)

        logger.debug(f"Generated {len(all_embeddings)} embeddings")
        return all_embeddings

    async def _extract_entities(self, chunk: Chunk) -> List[Entity]:
        """
        Extract entities from a chunk using LLM or basic extraction.

        Uses LLMEntityExtractor when self._use_llm_extraction is True,
        otherwise falls back to GeminiClient extraction.

        Args:
            chunk: Chunk to extract entities from

        Returns:
            List of extracted Entity objects with module_id tagging
        """
        # Try LLM extraction if enabled
        if getattr(self, "_use_llm_extraction", False) and getattr(
            self, "_llm_extractor", None
        ):
            try:
                llm_entities = await self._extract_entities_via_llm(chunk)
                if llm_entities:
                    logger.debug(
                        f"LLM extracted {len(llm_entities)} entities from chunk {chunk.id}"
                    )
                    return llm_entities
            except Exception as e:
                logger.warning(
                    f"LLM entity extraction failed for chunk {chunk.id}, "
                    f"falling back to basic extraction: {e}"
                )

        # Fallback to basic GeminiClient extraction
        raw_entities = await self.gemini.extract_entities(chunk.text, chunk.id)
        logger.debug(
            f"Extracted {len(raw_entities)} raw entities from chunk {chunk.id}"
        )

        # Convert to Entity objects
        entities = []
        for entity_data in raw_entities:
            entity = Entity(
                id=entity_data.get(
                    "id",
                    f"entity_{hashlib.md5(entity_data.get('name', '').encode()).hexdigest()[:12]}",
                ),
                name=entity_data.get("name", "Unknown"),
                entity_type=EntityType(entity_data.get("entity_type", "CONCEPT")),
                definition=entity_data.get("definition", ""),
                properties={
                    "category": entity_data.get("category", "General"),
                    "confidence": entity_data.get("confidence", 0.7),
                    "context_snippet": entity_data.get("context_snippet", ""),
                    "chunk_id": entity_data.get("chunk_id", chunk.id),
                    "extraction_method": "basic",
                },
            )
            entities.append(entity)

        logger.debug(f"Converted {len(entities)} entities from chunk {chunk.id}")
        return entities

    async def _extract_entities_via_llm(self, chunk: Chunk) -> List[Entity]:
        """
        Extract entities using LLMEntityExtractor.

        Provides higher quality extraction with confidence scoring
        and structured output.

        Args:
            chunk: Chunk to extract entities from

        Returns:
            List of Entity objects with extraction_method="llm"
        """
        if not self._llm_extractor:
            raise ValueError("LLMEntityExtractor not initialized")

        # Extract using LLM extractor
        extracted = await self._llm_extractor.extract_entities(
            text=chunk.text, doc_id=chunk.id
        )

        # Convert ExtractedEntity objects to Entity objects
        entities = []
        type_to_entity_type = {
            "Topic": EntityType.TOPIC,
            "Concept": EntityType.CONCEPT,
            "Methodology": EntityType.METHODOLOGY,
            "Finding": EntityType.FINDING,
        }

        for entity_type_key, extracted_list in extracted.items():
            for ext_entity in extracted_list:
                # Handle both ExtractedEntity objects and dict formats
                if hasattr(ext_entity, "name"):
                    # It's an ExtractedEntity object
                    name = ext_entity.name
                    entity_type_str = ext_entity.type
                    definition = ext_entity.definition
                    confidence = ext_entity.confidence_score
                    context = ext_entity.source_text or ""
                    category = ext_entity.category
                else:
                    # It's a dict (shouldn't happen but handle gracefully)
                    name = ext_entity.get("name", "")
                    entity_type_str = ext_entity.get("type", "Concept")
                    definition = ext_entity.get("definition", "")
                    confidence = ext_entity.get("confidence_score", 0.7)
                    context = ext_entity.get("source_text", "")
                    category = ext_entity.get("category", "General")

                if not name:
                    continue

                entity_type = type_to_entity_type.get(
                    entity_type_str, EntityType.CONCEPT
                )

                entity_id = f"{entity_type_str.lower()}_{hashlib.md5(name.lower().encode()).hexdigest()[:12]}"

                entity = Entity(
                    id=entity_id,
                    name=name,
                    entity_type=entity_type,
                    definition=definition,
                    properties={
                        "category": category,
                        "confidence": confidence,
                        "confidence_score": confidence,  # Also store as confidence_score for compatibility
                        "context_snippet": context[:200] if context else "",
                        "chunk_id": chunk.id,
                        "extraction_method": "llm",
                    },
                )
                entities.append(entity)

        # Log extraction statistics
        concepts_count = len(extracted.get("concepts", []))
        topics_count = len(extracted.get("topics", []))
        methodologies_count = len(extracted.get("methodologies", []))
        findings_count = len(extracted.get("findings", []))

        logger.info(
            f"Extracted via LLM: {concepts_count} concepts, {topics_count} topics, "
            f"{methodologies_count} methodologies, {findings_count} findings"
        )

        return entities

    def _deduplicate_entities(self, entities: List[Entity]) -> List[Entity]:
        """
        Deduplicate entities using exact name matching and semantic similarity.

        Follows patterns from AURA-CHAT/backend/llm_entity_extractor.py:
        - Phase 1: Exact name matching (case-insensitive)
        - Phase 2: Semantic similarity using embeddings (threshold: 0.85)

        Args:
            entities: List of entities to deduplicate

        Returns:
            Deduplicated list of entities
        """
        if not entities:
            return []

        # Phase 1: Exact name deduplication (fast)
        seen = {}
        for entity in entities:
            key = entity.name.lower().strip()
            if key not in seen:
                seen[key] = entity
            else:
                existing = seen[key]
                # Keep entity with higher confidence
                existing_confidence = existing.properties.get("confidence", 0)
                new_confidence = entity.properties.get("confidence", 0)
                if new_confidence > existing_confidence:
                    # Merge context snippets
                    existing_context = existing.properties.get("context_snippet", "")
                    new_context = entity.properties.get("context_snippet", "")
                    if existing_context and new_context:
                        existing.properties["context_snippet"] = (
                            f"{existing_context} ... {new_context}"
                        )
                    seen[key] = entity

        name_deduped = list(seen.values())
        logger.info(f"After exact deduplication: {len(name_deduped)} entities")

        # Phase 2: Semantic similarity deduplication
        if len(name_deduped) <= 3:
            return name_deduped

        try:
            return self._semantic_entity_deduplication(name_deduped)
        except Exception as e:
            logger.warning(f"Semantic deduplication failed: {e}")
            return name_deduped

    def _semantic_entity_deduplication(
        self,
        entities: List[Entity],
        similarity_threshold: float = ENTITY_DEDUP_SIMILARITY_THRESHOLD,
    ) -> List[Entity]:
        """
        Merge entities with high semantic similarity using embedding comparison.

        Args:
            entities: List of entities after name-based deduplication
            similarity_threshold: Cosine similarity threshold (default: 0.85)

        Returns:
            Deduplicated list with semantically similar entities merged
        """
        import numpy as np

        if len(entities) <= 1:
            return entities

        # Get embeddings for entity names
        entity_names = [e.name for e in entities]

        try:
            import google.generativeai as genai

            if self.gemini.api_key:
                genai.configure(api_key=self.gemini.api_key)
                embeddings = []
                for name in entity_names:
                    result = genai.embed_content(
                        model=self.gemini.embedding_model,
                        content=name,
                        task_type="semantic_similarity",
                    )
                    embeddings.append(result.get("embedding", []))
            else:
                raise ValueError("No API key")
        except Exception as e:
            logger.warning(f"Failed to get embeddings for semantic dedup: {e}")
            return entities

        if not embeddings or len(embeddings) != len(entities):
            return entities

        embeddings_array = np.array(embeddings)

        # Calculate pairwise cosine similarity
        norms = np.linalg.norm(embeddings_array, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1, norms)
        normalized = embeddings_array / norms
        similarity_matrix = np.dot(normalized, normalized.T)

        # Union-find for clustering
        n = len(entities)
        parent = list(range(n))

        def find(x):
            if parent[x] != x:
                parent[x] = find(parent[x])
            return parent[x]

        def union(x, y):
            px, py = find(x), find(y)
            if px != py:
                parent[px] = py

        # Union entities above threshold
        for i in range(n):
            for j in range(i + 1, n):
                if similarity_matrix[i, j] >= similarity_threshold:
                    union(i, j)

        # Group and merge
        clusters = {}
        for i in range(n):
            root = find(i)
            if root not in clusters:
                clusters[root] = []
            clusters[root].append(i)

        merged_entities = []
        for indices in clusters.values():
            if len(indices) == 1:
                merged_entities.append(entities[indices[0]])
            else:
                # Pick highest confidence as canonical
                cluster_entities = [entities[i] for i in indices]
                canonical = max(
                    cluster_entities, key=lambda e: e.properties.get("confidence", 0)
                )

                # Merge definitions and contexts
                all_definitions = [
                    e.definition for e in cluster_entities if e.definition
                ]
                if all_definitions:
                    canonical.definition = all_definitions[0]

                all_contexts = [
                    e.properties.get("context_snippet", "")
                    for e in cluster_entities
                    if e.properties.get("context_snippet")
                ]
                if all_contexts:
                    canonical.properties["context_snippet"] = " ... ".join(
                        all_contexts[:2]
                    )

                merged_entities.append(canonical)

        original_count = len(entities)
        merged_count = len(merged_entities)
        if merged_count < original_count:
            logger.info(
                f"Semantic deduplication: {original_count} -> {merged_count} entities"
            )

        return merged_entities

    def _prepare_entities_for_relationship_extraction(
        self, entities: List[Entity]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Prepare entities for relationship extraction by LLMEntityExtractor.

        Converts Entity objects to the dict format expected by
        extract_relationships().

        Args:
            entities: List of Entity objects

        Returns:
            Dict with keys: concepts, topics, methodologies, findings
        """
        result = {
            "concepts": [],
            "topics": [],
            "methodologies": [],
            "findings": [],
        }

        type_to_key = {
            EntityType.CONCEPT: "concepts",
            EntityType.TOPIC: "topics",
            EntityType.METHODOLOGY: "methodologies",
            EntityType.FINDING: "findings",
            EntityType.DEFINITION: "concepts",  # Map Definition to concepts
            EntityType.CITATION: "findings",  # Map Citation to findings
        }

        for entity in entities:
            key = type_to_key.get(entity.entity_type, "concepts")
            entity_dict = {
                "id": entity.id,
                "name": entity.name,
                "type": entity.entity_type.value,
                "definition": entity.definition,
                "confidence": entity.properties.get("confidence", 0.7),
                "context": entity.properties.get("context_snippet", ""),
            }
            result[key].append(entity_dict)

        return result

    def _build_entity_name_to_id_map(self, entities: List[Entity]) -> Dict[str, str]:
        """
        Build a case-insensitive map from entity name to entity ID.

        Args:
            entities: List of Entity objects

        Returns:
            Dict mapping lowercased name to entity ID
        """
        name_to_id = {}
        for entity in entities:
            name_key = entity.name.lower().strip()
            if name_key:
                name_to_id[name_key] = entity.id
        return name_to_id

    def _get_entity_type_by_name(
        self, name: str, entities: List[Entity]
    ) -> Optional[EntityType]:
        """
        Get entity type by entity name.

        Args:
            name: Entity name to look up
            entities: List of Entity objects

        Returns:
            EntityType if found, None otherwise
        """
        name_lower = name.lower().strip()
        for entity in entities:
            if entity.name.lower().strip() == name_lower:
                return entity.entity_type
        return None

    async def _store_entity_relationships(
        self,
        relationships: List[EntityRelationship],
        module_id: str,
        entities: List[Entity],
    ):
        """
        Store entity-entity relationships as edges in Neo4j.

        Creates edges between entity nodes with relationship type,
        confidence, and evidence properties.

        Args:
            relationships: List of Relationship objects from LLMEntityExtractor
            module_id: Module ID for filtering
            entities: List of Entity objects for name-to-ID lookup
        """
        if not self.driver:
            logger.warning("Neo4j driver not available for relationship storage")
            return

        if not relationships:
            return

        # Build name-to-ID map for resolving entity references
        name_to_id = self._build_entity_name_to_id_map(entities)

        stored_count = 0
        skipped_count = 0

        with self.driver.session() as session:
            for rel in relationships:
                try:
                    # Resolve entity names to IDs
                    source_key = rel.source_entity.lower().strip()
                    target_key = rel.target_entity.lower().strip()

                    source_id = name_to_id.get(source_key)
                    target_id = name_to_id.get(target_key)

                    if not source_id or not target_id:
                        logger.debug(
                            f"Skipping relationship: source={rel.source_entity}, "
                            f"target={rel.target_entity} (entity not found)"
                        )
                        skipped_count += 1
                        continue

                    # Get entity types for proper node matching
                    source_type = self._get_entity_type_by_name(
                        rel.source_entity, entities
                    )
                    target_type = self._get_entity_type_by_name(
                        rel.target_entity, entities
                    )

                    if not source_type or not target_type:
                        skipped_count += 1
                        continue

                    # Store relationship in Neo4j
                    await self._create_entity_relationship(
                        session,
                        source_id,
                        source_type.value,
                        target_id,
                        target_type.value,
                        rel.relationship_type,
                        rel.confidence,
                        rel.evidence,
                        module_id,
                    )
                    stored_count += 1

                except Exception as e:
                    logger.warning(f"Failed to store relationship: {e}")
                    skipped_count += 1

        logger.info(
            f"Stored {stored_count} entity-entity relationships "
            f"(skipped {skipped_count}) in Neo4j"
        )

    async def _create_entity_relationship(
        self,
        session,
        source_id: str,
        source_type: str,
        target_id: str,
        target_type: str,
        rel_type: str,
        confidence: float,
        evidence: Optional[str],
        module_id: str,
    ):
        """
        Create a single entity-entity relationship in Neo4j.

        Since Neo4j doesn't support parameterized relationship types,
        we use conditional queries for each relationship type.

        Args:
            session: Neo4j session
            source_id: Source entity ID
            source_type: Source entity type (Concept, Topic, etc.)
            target_id: Target entity ID
            target_type: Target entity type
            rel_type: Relationship type (DEFINES, USES, etc.)
            confidence: Confidence score
            evidence: Optional evidence text
            module_id: Module ID for filtering
        """
        # Build relationship query based on relationship type
        # Neo4j doesn't allow parameterized relationship types, so we use
        # dynamic query construction (safe since rel_type is validated)
        valid_rel_types = [
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

        if rel_type not in valid_rel_types:
            rel_type = "RELATED_TO"

        query = f"""
        MATCH (source:{source_type} {{id: $source_id, module_id: $module_id}})
        MATCH (target:{target_type} {{id: $target_id, module_id: $module_id}})
        MERGE (source)-[r:{rel_type}]->(target)
        SET r.confidence = $confidence,
            r.evidence = $evidence,
            r.created_at = datetime()
        RETURN r
        """

        params = {
            "source_id": source_id,
            "target_id": target_id,
            "module_id": module_id,
            "confidence": confidence,
            "evidence": evidence[:300] if evidence else None,
        }

        session.run(query, params)

    async def _generate_and_store_entity_embeddings(
        self,
        entities: List[Entity],
        module_id: str,
    ) -> int:
        """
        Generate embeddings for entities and store them in Neo4j.

        Uses EmbeddingService to generate 768-dimensional embeddings for
        each entity based on name + definition, then updates the entity
        nodes in Neo4j with the embedding property.

        Args:
            entities: List of Entity objects to embed
            module_id: Module ID for filtering

        Returns:
            Number of entities successfully embedded
        """
        if not entities:
            return 0

        if not self.driver:
            logger.warning("Neo4j driver not available for entity embedding storage")
            return 0

        try:
            # Initialize embedding service
            embedding_service = EmbeddingService(api_key=self.gemini.api_key)

            # Generate embeddings using the service
            entity_embeddings = embedding_service.embed_entities(entities)

            if not entity_embeddings:
                logger.warning("No embeddings generated for entities")
                return 0

            # Store embeddings in Neo4j
            embedded_count = 0
            with self.driver.session() as session:
                for entity in entities:
                    embedding = entity_embeddings.get(entity.id)
                    if not embedding:
                        continue

                    try:
                        await self._update_entity_embedding(
                            session,
                            entity.id,
                            entity.entity_type.value,
                            embedding,
                            module_id,
                        )
                        embedded_count += 1
                    except Exception as e:
                        logger.warning(
                            f"Failed to store embedding for entity {entity.id}: {e}"
                        )

            logger.info(
                f"Stored embeddings for {embedded_count}/{len(entities)} entities"
            )
            return embedded_count

        except Exception as e:
            logger.error(f"Entity embedding generation failed: {e}")
            return 0

    async def _update_entity_embedding(
        self,
        session,
        entity_id: str,
        entity_type: str,
        embedding: List[float],
        module_id: str,
    ):
        """
        Update a single entity node with its embedding.

        Args:
            session: Neo4j session
            entity_id: Entity ID
            entity_type: Entity type (Concept, Topic, etc.)
            embedding: 768-dimensional embedding vector
            module_id: Module ID for filtering
        """
        query = f"""
        MATCH (e:{entity_type} {{id: $entity_id, module_id: $module_id}})
        SET e.embedding = $embedding,
            e.embedded_at = datetime()
        RETURN e.id
        """

        params = {
            "entity_id": entity_id,
            "module_id": module_id,
            "embedding": embedding,
        }

        session.run(query, params)

    async def _store_in_neo4j(
        self,
        document_id: str,
        module_id: str,
        user_id: str,
        chunks: List[Chunk],
        entities: List[Entity],
    ):
        """
        Store document, chunks, and entities in Neo4j with module_id tagging.

        All nodes are tagged with module_id for filtering and access control.

        Args:
            document_id: Document identifier
            module_id: Module ID for tagging
            user_id: User who owns the document
            chunks: List of processed chunks
            entities: List of extracted entities
        """
        if not self.driver:
            raise ValueError("Neo4j driver not available")

        with self.driver.session() as session:
            # Step 1: Create or update Document node with module_id
            await self._create_document_node(
                session, document_id, module_id, user_id, chunks
            )

            # Step 2: Create Chunk nodes with embeddings and module_id
            for chunk in chunks:
                await self._create_chunk_node(session, chunk, module_id)

                # Step 3: Link Document to Chunk
                await self._create_doc_chunk_relationship(
                    session, document_id, chunk.id
                )

                # Step 4: Create Entity nodes from chunk entities
                for entity in chunk.entities:
                    await self._create_entity_node(session, entity, module_id)

                    # Step 5: Link Chunk to Entity with relevance score from confidence
                    relevance_score = entity.properties.get("confidence", 0.7)
                    await self._create_chunk_entity_relationship(
                        session, chunk.id, entity.id, relevance_score
                    )

        logger.info(
            f"Stored in Neo4j: document={document_id}, "
            f"chunks={len(chunks)}, entities={len(entities)}"
        )

    async def _create_document_node(
        self, session, document_id: str, module_id: str, user_id: str, chunks: List
    ):
        """Create or update Document node with module_id."""
        query = """
        MERGE (d:Document {id: $id})
        SET d.module_id = $module_id,
            d.user_id = $user_id,
            d.chunk_count = $chunk_count,
            d.updated_at = $updated_at
        RETURN d.id
        """
        session.run(
            query,
            {
                "id": document_id,
                "module_id": module_id,
                "user_id": user_id,
                "chunk_count": len(chunks),
                "updated_at": datetime.utcnow().isoformat(),
            },
        )

    async def _create_chunk_node(self, session, chunk: Chunk, module_id: str):
        """Create Chunk node with embedding and module_id."""
        query = """
        MERGE (c:Chunk {id: $id})
        SET c.text = $text,
            c.token_count = $token_count,
            c.index = $index,
            c.module_id = $module_id,
            c.embedding = $embedding
        RETURN c.id
        """
        params = {
            "id": chunk.id,
            "text": chunk.text[:10000],  # Limit text size for Neo4j
            "token_count": chunk.token_count,
            "index": chunk.index,
            "module_id": module_id,
            "embedding": chunk.embedding,
        }
        session.run(query, params)

    async def _create_doc_chunk_relationship(self, session, doc_id: str, chunk_id: str):
        """Create HAS_CHUNK relationship."""
        query = """
        MATCH (d:Document {id: $doc_id})
        MATCH (c:Chunk {id: $chunk_id})
        MERGE (d)-[r:HAS_CHUNK]->(c)
        RETURN r
        """
        session.run(query, {"doc_id": doc_id, "chunk_id": chunk_id})

    async def _create_entity_node(self, session, entity: Entity, module_id: str):
        """Create entity node (Topic, Concept, etc.) with module_id and properties."""
        query = f"""
        MERGE (e:{entity.entity_type.value} {{id: $id}})
        SET e.name = $name,
            e.definition = $definition,
            e.module_id = $module_id,
            e.category = $category,
            e.confidence = $confidence,
            e.confidence_score = $confidence_score,
            e.extraction_method = $extraction_method,
            e.context_snippet = $context_snippet,
            e.chunk_id = $chunk_id,
            e.embedding = $embedding
        RETURN e.id
        """
        params = {
            "id": entity.id,
            "name": entity.name,
            "definition": entity.definition,
            "module_id": module_id,
            "category": entity.properties.get("category", "General"),
            "confidence": entity.properties.get("confidence", 0.7),
            "confidence_score": entity.properties.get(
                "confidence_score", entity.properties.get("confidence", 0.7)
            ),
            "extraction_method": entity.properties.get("extraction_method", "basic"),
            "context_snippet": entity.properties.get("context_snippet", "")[:200],
            "chunk_id": entity.properties.get("chunk_id", ""),
            "embedding": entity.embedding,
        }
        session.run(query, params)

    async def _create_chunk_entity_relationship(
        self, session, chunk_id: str, entity_id: str, relevance_score: float = 1.0
    ):
        """Create CONTAINS_ENTITY relationship with relevance score."""
        query = """
        MATCH (c:Chunk {id: $chunk_id})
        MATCH (e) WHERE e.id = $entity_id
        MERGE (c)-[r:CONTAINS_ENTITY]->(e)
        SET r.relevance_score = $relevance_score
        RETURN r
        """
        session.run(
            query,
            {
                "chunk_id": chunk_id,
                "entity_id": entity_id,
                "relevance_score": relevance_score,
            },
        )


async def process_document_simple(
    document_id: str, module_id: str, user_id: str, file_path: str = None
) -> Dict[str, Any]:
    """
    Simple document processing function for basic usage.

    Creates a processor and processes the document in one call.

    Args:
        document_id: Document identifier
        module_id: Module ID for tagging
        user_id: User who owns the document
        file_path: Optional path to document file

    Returns:
        Processing result dict
    """
    processor = KnowledgeGraphProcessor()
    return await processor.process_document(
        document_id, module_id, user_id, file_path=file_path
    )
