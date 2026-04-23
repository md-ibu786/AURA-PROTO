"""
============================================================================
FILE: test_chunk_labeling.py
LOCATION: api/tests/test_chunk_labeling.py
============================================================================

PURPOSE:
    Unit tests for chunk labeling feature (Phase 10).

ROLE IN PROJECT:
    Validates label generation, LLM fallback, JSON extraction, and
    heuristic labeling in the KnowledgeGraphProcessor pipeline.

KEY COMPONENTS:
    - processor fixture
    - sample_chunks fixture
    - TestExtractJsonArray
    - TestHeuristicLabel
    - TestGenerateChunkLabels
    - TestLabelSingleBatch

DEPENDENCIES:
    - External: pytest, unittest.mock
    - Internal: api.kg_processor

USAGE:
    pytest api/tests/test_chunk_labeling.py -v
============================================================================
"""

import sys
import types
from dataclasses import dataclass
from unittest.mock import AsyncMock
from unittest.mock import MagicMock

import pytest


def _register_module(name: str, module: types.ModuleType) -> None:
    """Register import shim module for test-only dependency isolation."""
    sys.modules.setdefault(name, module)


if 'services.llm_entity_extractor' not in sys.modules:
    llm_module = types.ModuleType('services.llm_entity_extractor')

    class LLMEntityExtractor:
        """Minimal test shim for import-time dependency."""

    class Relationship:
        """Minimal test shim for import-time dependency."""

    @dataclass
    class ExtractionResult:
        """Minimal test shim for import-time dependency."""

        entities: dict

    def merge_extraction_results(*args, **kwargs):
        """Return empty merged result for import shim."""
        del args, kwargs
        return ExtractionResult(entities={})

    llm_module.LLMEntityExtractor = LLMEntityExtractor
    llm_module.Relationship = Relationship
    llm_module.ExtractionResult = ExtractionResult
    llm_module.merge_extraction_results = merge_extraction_results
    _register_module('services.llm_entity_extractor', llm_module)


if 'services.embeddings' not in sys.modules:
    embeddings_module = types.ModuleType('services.embeddings')

    class EmbeddingService:
        """Minimal test shim for import-time dependency."""

    embeddings_module.EmbeddingService = EmbeddingService
    _register_module('services.embeddings', embeddings_module)


if 'services.entity_aware_chunker' not in sys.modules:
    chunker_module = types.ModuleType('services.entity_aware_chunker')

    class EntityAwareChunker:
        """Minimal test shim for import-time dependency."""

        def __init__(self, chunker_config: dict | None = None):
            self.chunker_config = chunker_config or {}

    chunker_module.EntityAwareChunker = EntityAwareChunker
    _register_module('services.entity_aware_chunker', chunker_module)


if 'services.entity_deduplicator' not in sys.modules:
    dedup_module = types.ModuleType('services.entity_deduplicator')

    class EntityDeduplicator:
        """Minimal test shim for import-time dependency."""

    dedup_module.EntityDeduplicator = EntityDeduplicator
    _register_module('services.entity_deduplicator', dedup_module)


if 'services.document_parsers.docx_parser' not in sys.modules:
    docx_module = types.ModuleType('services.document_parsers.docx_parser')

    class DocxParser:
        """Minimal test shim for import-time dependency."""

    class DocxParseError(Exception):
        """Minimal test shim for import-time dependency."""

    class CorruptedDocxError(Exception):
        """Minimal test shim for import-time dependency."""

    class PasswordProtectedDocxError(Exception):
        """Minimal test shim for import-time dependency."""

    class EmptyDocxError(Exception):
        """Minimal test shim for import-time dependency."""

    docx_module.DocxParser = DocxParser
    docx_module.DocxParseError = DocxParseError
    docx_module.CorruptedDocxError = CorruptedDocxError
    docx_module.PasswordProtectedDocxError = PasswordProtectedDocxError
    docx_module.EmptyDocxError = EmptyDocxError
    _register_module('services.document_parsers.docx_parser', docx_module)


if 'services.extraction_templates' not in sys.modules:
    templates_module = types.ModuleType('services.extraction_templates')

    def get_template_registry():
        """Minimal test shim for import-time dependency."""
        return {}

    def get_template_extractor(*args, **kwargs):
        """Minimal test shim for import-time dependency."""
        del args, kwargs
        return None

    templates_module.get_template_registry = get_template_registry
    templates_module.get_template_extractor = get_template_extractor
    _register_module('services.extraction_templates', templates_module)

from api.kg_processor import Chunk
from api.kg_processor import GeminiClient
from api.kg_processor import KnowledgeGraphProcessor


@pytest.fixture
def processor() -> KnowledgeGraphProcessor:
    """Create KnowledgeGraphProcessor with mocked dependencies."""
    mock_driver = MagicMock()
    mock_gemini = MagicMock(spec=GeminiClient)
    mock_gemini.generate_text = AsyncMock()
    return KnowledgeGraphProcessor(
        driver=mock_driver,
        gemini_client=mock_gemini,
    )


@pytest.fixture
def sample_chunks() -> list[Chunk]:
    """Create sample chunks for labeling tests."""
    return [
        Chunk(
            id='chunk_doc1_0',
            text='The zeroth law of thermodynamics.',
            index=0,
            token_count=8,
        ),
        Chunk(
            id='chunk_doc1_1',
            text='The first law states energy is conserved.',
            index=1,
            token_count=9,
        ),
        Chunk(
            id='chunk_doc1_2',
            text='Entropy always increases per the second law.',
            index=2,
            token_count=9,
        ),
    ]


class TestExtractJsonArray:
    """Tests for _extract_json_array."""

    def test_valid_json_array(self, processor: KnowledgeGraphProcessor) -> None:
        """Extract valid raw JSON array."""
        result = processor._extract_json_array(
            '[["Label A", "Label B"], ["Label C"]]'
        )
        assert result == [['Label A', 'Label B'], ['Label C']]

    def test_json_array_with_surrounding_text(
        self, processor: KnowledgeGraphProcessor
    ) -> None:
        """Extract JSON array when response includes extra prose."""
        result = processor._extract_json_array(
            'Here are labels: [["A"], ["B"]] done.'
        )
        assert result == [['A'], ['B']]

    def test_no_brackets_returns_empty(
        self, processor: KnowledgeGraphProcessor
    ) -> None:
        """Return empty list when no JSON array markers exist."""
        result = processor._extract_json_array('no json here')
        assert result == []

    def test_malformed_json_returns_empty(
        self, processor: KnowledgeGraphProcessor
    ) -> None:
        """Return empty list on malformed JSON content."""
        result = processor._extract_json_array('[["unclosed')
        assert result == []

    def test_empty_array(self, processor: KnowledgeGraphProcessor) -> None:
        """Accept empty JSON array."""
        result = processor._extract_json_array('[]')
        assert result == []


class TestHeuristicLabel:
    """Tests for _heuristic_label."""

    def test_short_first_sentence(
        self, processor: KnowledgeGraphProcessor
    ) -> None:
        """Use first sentence when under truncation threshold."""
        result = processor._heuristic_label(
            'Thermodynamics basics. More text here.'
        )
        assert result == ['Thermodynamics basics']

    def test_long_first_sentence_truncates(
        self, processor: KnowledgeGraphProcessor
    ) -> None:
        """Truncate long first sentence to 60 chars plus ellipsis."""
        long_text = f"{'A' * 100}. Second sentence."
        result = processor._heuristic_label(long_text)
        assert len(result) == 1
        assert len(result[0]) == 63
        assert result[0].endswith('...')

    def test_no_period(self, processor: KnowledgeGraphProcessor) -> None:
        """Return whole string when no sentence separator exists."""
        result = processor._heuristic_label('Short text without period')
        assert result == ['Short text without period']


@pytest.mark.asyncio
class TestGenerateChunkLabels:
    """Tests for _generate_chunk_labels."""

    async def test_success(
        self,
        processor: KnowledgeGraphProcessor,
        sample_chunks: list[Chunk],
    ) -> None:
        """Assign labels when LLM output count matches chunk count."""
        processor.gemini.generate_text.return_value = (
            '[["Zeroth Law", "Thermodynamics"], '
            '["First Law", "Energy"], '
            '["Second Law", "Entropy"]]'
        )

        await processor._generate_chunk_labels(sample_chunks)

        assert sample_chunks[0].chunk_labels == [
            'Zeroth Law',
            'Thermodynamics',
        ]
        assert sample_chunks[1].chunk_labels == ['First Law', 'Energy']
        assert sample_chunks[2].chunk_labels == ['Second Law', 'Entropy']

    async def test_empty_chunks(
        self, processor: KnowledgeGraphProcessor
    ) -> None:
        """Skip LLM call when chunk list is empty."""
        await processor._generate_chunk_labels([])
        processor.gemini.generate_text.assert_not_called()

    async def test_mismatch_falls_back(
        self,
        processor: KnowledgeGraphProcessor,
        sample_chunks: list[Chunk],
    ) -> None:
        """Fallback to heuristic labels when count mismatches."""
        processor.gemini.generate_text.return_value = '[["Only One"]]'

        await processor._generate_chunk_labels(sample_chunks)

        for chunk in sample_chunks:
            assert chunk.chunk_labels is not None
            assert isinstance(chunk.chunk_labels, list)
            assert len(chunk.chunk_labels) > 0

    async def test_llm_failure_falls_back(
        self,
        processor: KnowledgeGraphProcessor,
        sample_chunks: list[Chunk],
    ) -> None:
        """Fallback to heuristic labels when LLM call fails."""
        processor.gemini.generate_text.side_effect = RuntimeError('API error')

        await processor._generate_chunk_labels(sample_chunks)

        for chunk in sample_chunks:
            assert chunk.chunk_labels is not None
            assert isinstance(chunk.chunk_labels, list)
            assert len(chunk.chunk_labels) > 0
            assert all(
                isinstance(label, str) and len(label) > 0
                for label in chunk.chunk_labels
            )


@pytest.mark.asyncio
class TestLabelSingleBatch:
    """Tests for _label_single_batch."""

    async def test_batch_prompt_contains_excerpts(
        self, processor: KnowledgeGraphProcessor
    ) -> None:
        """Prompt should include numbered excerpt entries."""
        texts = ['Text one.', 'Text two.']
        processor.gemini.generate_text.return_value = (
            '[["Label 1"], ["Label 2"]]'
        )

        result = await processor._label_single_batch(texts)

        prompt = processor.gemini.generate_text.call_args[0][0]
        assert 'Excerpt 1:' in prompt
        assert 'Excerpt 2:' in prompt
        assert result == [['Label 1'], ['Label 2']]

    async def test_batch_truncates_to_200_chars(
        self, processor: KnowledgeGraphProcessor
    ) -> None:
        """Long excerpts should be truncated to max 200 chars in prompt."""
        long_text = 'A' * 500
        processor.gemini.generate_text.return_value = '[["Long Label"]]'

        await processor._label_single_batch([long_text])

        prompt = processor.gemini.generate_text.call_args[0][0]
        assert ('A' * 201) not in prompt
