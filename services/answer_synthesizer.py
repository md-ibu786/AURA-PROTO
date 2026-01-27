# answer_synthesizer.py
# Service for synthesizing answers from multiple document contexts using Gemini

# Provides multi-source answer synthesis with citation tracking, contradiction
# detection, and confidence scoring. Uses Gemini LLM to generate comprehensive
# answers from retrieved document contexts while maintaining source attribution.

# @see: services/vertex_ai_client.py - Vertex AI Gemini client wrapper
# @see: services/query_analyzer.py - Query analysis for intent detection
# @note: Gracefully degrades when Vertex AI is unavailable

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

from api.config import LLM_SUMMARIZATION_MODEL
from services.vertex_ai_client import GenerationConfig, generate_content, get_model


# ============================================================================
# LOGGING
# ============================================================================

logger = logging.getLogger(__name__)


# ============================================================================
# DATA MODELS
# ============================================================================


class DocumentContext(BaseModel):
    """Context from a single document including relevant chunks and metadata."""

    document_id: str = Field(description="Unique identifier for the document")
    document_title: str = Field(description="Title of the document")
    module_id: str = Field(description="Module/course ID the document belongs to")
    chunks: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Relevant chunks [{id, text, score}]",
    )
    entities: List[str] = Field(
        default_factory=list,
        description="Entities mentioned in the document",
    )
    relevance_score: float = Field(
        ge=0.0,
        le=1.0,
        description="Overall relevance score for the document",
    )


class Citation(BaseModel):
    """A citation linking answer content to source material."""

    reference_id: str = Field(description="Citation reference e.g., '[1]'")
    document_id: str = Field(description="Source document ID")
    document_title: str = Field(description="Source document title")
    chunk_id: str = Field(description="Specific chunk ID cited")
    chunk_text: str = Field(description="Text content of the cited chunk")
    position: int = Field(
        ge=0,
        description="Position of citation in the answer (character index)",
    )


class ContradictionInfo(BaseModel):
    """Information about contradicting statements found across sources."""

    topic: str = Field(description="Topic where contradiction was found")
    source_a: str = Field(description="First source document title")
    statement_a: str = Field(description="Statement from first source")
    source_b: str = Field(description="Second source document title")
    statement_b: str = Field(description="Statement from second source")
    resolution_hint: Optional[str] = Field(
        default=None,
        description="Optional hint on how to resolve the contradiction",
    )


class SynthesizedAnswer(BaseModel):
    """Complete synthesized answer with metadata and citations."""

    answer: str = Field(description="The synthesized answer text")
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence score based on source quality and agreement",
    )
    sources_used: int = Field(
        ge=0,
        description="Number of source documents used in synthesis",
    )
    key_points: List[str] = Field(
        default_factory=list,
        description="Key points extracted from the answer",
    )
    citations: List[Citation] = Field(
        default_factory=list,
        description="Citations linking answer to sources",
    )
    contradictions: List[ContradictionInfo] = Field(
        default_factory=list,
        description="Contradictions found across sources",
    )


class SynthesisOptions(BaseModel):
    """Configuration options for answer synthesis."""

    max_answer_length: int = Field(
        default=1500,
        ge=100,
        le=10000,
        description="Maximum length of synthesized answer in characters",
    )
    citation_style: Literal["inline", "footnote", "reference"] = Field(
        default="inline",
        description="Citation style to use in the answer",
    )
    detect_contradictions: bool = Field(
        default=True,
        description="Whether to detect and report contradictions",
    )
    include_key_points: bool = Field(
        default=True,
        description="Whether to include key points summary",
    )


# ============================================================================
# PROMPT TEMPLATES
# ============================================================================

SYNTHESIS_PROMPT_TEMPLATE = """You are analyzing multiple documents to answer \
a question.

Question: {query}

Documents and relevant excerpts:
{formatted_contexts}

Instructions:
1. Synthesize a comprehensive answer using information from multiple sources
2. Use [1], [2], etc. to cite sources inline
3. If sources contradict, note the contradiction and explain
4. List key points at the end
5. Rate your confidence (0.0-1.0) based on source quality and agreement

Format your response EXACTLY as:
ANSWER: <your synthesized answer with [N] citations>
KEY_POINTS:
- Point 1
- Point 2
CONFIDENCE: <0.0-1.0>
CONTRADICTIONS: <list any contradictions found, or "None">
"""


# ============================================================================
# ANSWER SYNTHESIZER CLASS
# ============================================================================


class AnswerSynthesizer:
    """
    Synthesizes answers from multiple document contexts using Gemini LLM.

    Provides multi-source answer synthesis with:
    - Inline citation tracking ([1], [2], etc.)
    - Contradiction detection across sources
    - Confidence scoring based on source agreement
    - Key points extraction
    - Graceful degradation when LLM is unavailable

    Example:
        synthesizer = AnswerSynthesizer()

        contexts = [
            DocumentContext(
                document_id="doc1",
                document_title="Neural Networks Basics",
                module_id="CS101",
                chunks=[{"id": "c1", "text": "...", "score": 0.9}],
                entities=["neural network", "backpropagation"],
                relevance_score=0.85,
            ),
        ]

        result = await synthesizer.synthesize(
            query="What is backpropagation?",
            contexts=contexts,
        )
        # SynthesizedAnswer with answer, citations, key_points, etc.
    """

    def __init__(self, model_name: str = LLM_SUMMARIZATION_MODEL):
        """
        Initialize AnswerSynthesizer with specified model.

        Args:
            model_name: Vertex AI Gemini model to use for synthesis.
        """
        self.model_name = model_name
        self._model = None
        logger.info(f"AnswerSynthesizer initialized with model={model_name}")

        # Check if Vertex AI is available
        model = self._get_model()
        if model is None:
            logger.warning("Vertex AI not available, returning fallback response")
            return self._build_fallback_response(query, contexts)

        # Build prompt and call LLM
        prompt = self._build_synthesis_prompt(query, contexts)

        try:
            response = generate_content(
                model,
                prompt,
                generation_config=GenerationConfig(
                    temperature=0.2,
                    max_output_tokens=4096,
                ),
            )
            response_text = response.text
        except Exception as e:
            logger.error(f"LLM synthesis failed: {e}")
            return self._build_fallback_response(query, contexts)

        # Parse the response
        parsed = self._parse_synthesis_response(response_text)

        # Extract citations from the answer
        answer_text = parsed.get("answer", "")
        citations = self._extract_citations(answer_text, contexts)
        citations = self._validate_citations(citations, contexts)

        # Parse contradictions if present
        contradictions = self._parse_contradictions(
            parsed.get("contradictions", "None"),
            contexts,
        )

        # Build final response
        key_points = parsed.get("key_points", [])
        if not options.include_key_points:
            key_points = []

        confidence = parsed.get("confidence", 0.5)

        return SynthesizedAnswer(
            answer=answer_text[: options.max_answer_length],
            confidence=confidence,
            sources_used=len(contexts),
            key_points=key_points,
            citations=citations,
            contradictions=contradictions if options.detect_contradictions else [],
        )

    def _build_synthesis_prompt(
        self,
        query: str,
        contexts: List[DocumentContext],
    ) -> str:
        """
        Build the LLM prompt with contexts formatted for synthesis.

        Args:
            query: The user's question.
            contexts: List of document contexts.

        Returns:
            Formatted prompt string.
        """
        formatted_contexts = []

        for idx, ctx in enumerate(contexts, 1):
            doc_section = f"[{idx}] {ctx.document_title} (Module: {ctx.module_id})"
            doc_section += f"\nRelevance: {ctx.relevance_score:.2f}"

            if ctx.entities:
                doc_section += f"\nEntities: {', '.join(ctx.entities[:5])}"

            doc_section += "\nExcerpts:"
            for chunk in ctx.chunks:
                chunk_text = chunk.get("text", "")[:500]  # Limit chunk length
                chunk_score = chunk.get("score", 0.0)
                doc_section += f"\n  - (score: {chunk_score:.2f}) {chunk_text}"

            formatted_contexts.append(doc_section)

        contexts_str = "\n\n".join(formatted_contexts)

        return SYNTHESIS_PROMPT_TEMPLATE.format(
            query=query,
            formatted_contexts=contexts_str,
        )

    def _parse_synthesis_response(self, response_text: str) -> Dict[str, Any]:
        """
        Parse the structured LLM response into components.

        Args:
            response_text: Raw LLM response text.

        Returns:
            Dict with 'answer', 'key_points', 'confidence', 'contradictions'.
        """
        result = {
            "answer": "",
            "key_points": [],
            "confidence": 0.5,
            "contradictions": "None",
        }

        if not response_text:
            return result

        # Extract ANSWER section
        answer_match = re.search(
            r"ANSWER:\s*(.*?)(?=KEY_POINTS:|CONFIDENCE:|CONTRADICTIONS:|$)",
            response_text,
            re.DOTALL | re.IGNORECASE,
        )
        if answer_match:
            result["answer"] = answer_match.group(1).strip()

        # Extract KEY_POINTS section
        key_points_match = re.search(
            r"KEY_POINTS:\s*(.*?)(?=CONFIDENCE:|CONTRADICTIONS:|$)",
            response_text,
            re.DOTALL | re.IGNORECASE,
        )
        if key_points_match:
            points_text = key_points_match.group(1).strip()
            # Parse bullet points
            points = re.findall(r"[-•*]\s*(.+?)(?=\n[-•*]|\n\n|$)", points_text)
            result["key_points"] = [p.strip() for p in points if p.strip()]

        # Extract CONFIDENCE section
        confidence_match = re.search(
            r"CONFIDENCE:\s*([\d.]+)",
            response_text,
            re.IGNORECASE,
        )
        if confidence_match:
            try:
                confidence = float(confidence_match.group(1))
                result["confidence"] = max(0.0, min(1.0, confidence))
            except ValueError:
                result["confidence"] = 0.5

        # Extract CONTRADICTIONS section
        contradictions_match = re.search(
            r"CONTRADICTIONS:\s*(.*?)$",
            response_text,
            re.DOTALL | re.IGNORECASE,
        )
        if contradictions_match:
            result["contradictions"] = contradictions_match.group(1).strip()

        return result

    def _extract_citations(
        self,
        answer_text: str,
        contexts: List[DocumentContext],
    ) -> List[Citation]:
        """
        Extract [1], [2], etc. citations from answer and map to sources.

        Args:
            answer_text: The synthesized answer with inline citations.
            contexts: Original document contexts for mapping.

        Returns:
            List of Citation objects.
        """
        citations = []

        # Find all citation patterns [N]
        citation_pattern = re.compile(r"\[(\d+)\]")
        matches = citation_pattern.finditer(answer_text)

        for match in matches:
            ref_num = int(match.group(1))
            ref_id = f"[{ref_num}]"
            position = match.start()

            # Map to context (1-indexed)
            if 1 <= ref_num <= len(contexts):
                ctx = contexts[ref_num - 1]

                # Get first chunk as representative
                chunk_id = ""
                chunk_text = ""
                if ctx.chunks:
                    first_chunk = ctx.chunks[0]
                    chunk_id = first_chunk.get("id", f"chunk_{ref_num}")
                    chunk_text = first_chunk.get("text", "")[:200]

                citations.append(
                    Citation(
                        reference_id=ref_id,
                        document_id=ctx.document_id,
                        document_title=ctx.document_title,
                        chunk_id=chunk_id,
                        chunk_text=chunk_text,
                        position=position,
                    )
                )

        return citations

    def _validate_citations(
        self,
        citations: List[Citation],
        contexts: List[DocumentContext],
    ) -> List[Citation]:
        """
        Validate that citations reference valid sources.

        Args:
            citations: List of extracted citations.
            contexts: Original document contexts.

        Returns:
            List of validated citations (invalid ones removed).
        """
        valid_doc_ids = {ctx.document_id for ctx in contexts}
        validated = []

        for citation in citations:
            if citation.document_id in valid_doc_ids:
                validated.append(citation)
            else:
                logger.warning(
                    f"Invalid citation {citation.reference_id}: "
                    f"document_id {citation.document_id} not in contexts"
                )

        return validated

    def _parse_contradictions(
        self,
        contradictions_text: str,
        contexts: List[DocumentContext],
    ) -> List[ContradictionInfo]:
        """
        Parse contradiction text into structured ContradictionInfo objects.

        Args:
            contradictions_text: Raw contradictions text from LLM response.
            contexts: Original document contexts.

        Returns:
            List of ContradictionInfo objects.
        """
        if not contradictions_text or contradictions_text.lower() == "none":
            return []

        contradictions = []

        # Simple parsing: look for patterns like "Source A says X, but Source B says Y"
        # This is a basic implementation; could be enhanced with more robust parsing
        lines = contradictions_text.split("\n")

        for line in lines:
            line = line.strip()
            if not line or line.lower() == "none":
                continue

            # Try to extract source references
            source_refs = re.findall(r"\[(\d+)\]", line)

            if len(source_refs) >= 2:
                # Found at least two source references
                source_a_idx = int(source_refs[0]) - 1
                source_b_idx = int(source_refs[1]) - 1

                source_a = (
                    contexts[source_a_idx].document_title
                    if 0 <= source_a_idx < len(contexts)
                    else f"Source {source_refs[0]}"
                )
                source_b = (
                    contexts[source_b_idx].document_title
                    if 0 <= source_b_idx < len(contexts)
                    else f"Source {source_refs[1]}"
                )

                contradictions.append(
                    ContradictionInfo(
                        topic="See description",
                        source_a=source_a,
                        statement_a=line,
                        source_b=source_b,
                        statement_b=line,
                        resolution_hint=None,
                    )
                )
            elif line and line.lower() not in ("none", "-"):
                # Generic contradiction without clear source references
                contradictions.append(
                    ContradictionInfo(
                        topic="General",
                        source_a="Multiple sources",
                        statement_a=line,
                        source_b="Multiple sources",
                        statement_b=line,
                        resolution_hint=None,
                    )
                )

        return contradictions

    def _build_fallback_response(
        self,
        query: str,
        contexts: List[DocumentContext],
    ) -> SynthesizedAnswer:
        """
        Build a fallback response when LLM is unavailable.

        Concatenates relevant excerpts from contexts without synthesis.

        Args:
            query: The user's question.
            contexts: List of document contexts.

        Returns:
            SynthesizedAnswer with concatenated excerpts.
        """
        logger.info("Building fallback response without LLM synthesis")

        # Collect excerpts from all contexts
        excerpts = []
        citations = []

        for idx, ctx in enumerate(contexts, 1):
            ref_id = f"[{idx}]"

            for chunk in ctx.chunks[:2]:  # Limit to 2 chunks per document
                chunk_text = chunk.get("text", "")[:300]
                chunk_id = chunk.get("id", f"chunk_{idx}")

                if chunk_text:
                    excerpts.append(f"{ref_id} {chunk_text}")
                    citations.append(
                        Citation(
                            reference_id=ref_id,
                            document_id=ctx.document_id,
                            document_title=ctx.document_title,
                            chunk_id=chunk_id,
                            chunk_text=chunk_text,
                            position=len("\n\n".join(excerpts[:-1])) if excerpts else 0,
                        )
                    )

        answer = (
            f"Based on the available documents for '{query}':\n\n"
            + "\n\n".join(excerpts[:5])  # Limit to 5 excerpts
        )

        # Generate simple key points from document titles
        key_points = [f"Information from: {ctx.document_title}" for ctx in contexts[:3]]

        return SynthesizedAnswer(
            answer=answer[:1500],
            confidence=0.3,  # Low confidence for fallback
            sources_used=len(contexts),
            key_points=key_points,
            citations=citations,
            contradictions=[],
        )


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================


def create_answer_synthesizer(
    model_name: str = "gemini-1.5-flash",
) -> AnswerSynthesizer:
    """
    Factory function to create AnswerSynthesizer.

    Args:
        model_name: Gemini model to use for synthesis.

    Returns:
        Configured AnswerSynthesizer instance.
    """
    return AnswerSynthesizer(model_name=model_name)
