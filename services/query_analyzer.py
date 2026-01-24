# query_analyzer.py
# Query analysis service for understanding query intent and extracting key terms

# Analyzes search queries to determine intent (factual, conceptual, comparative, etc.)
# and extract key terms for entity lookup. Supports query expansion and future
# features like answer synthesis by understanding what the user is asking for.

# @see: api/rag_engine.py - Uses QueryAnalyzer for query expansion
# @see: api/schemas/search.py - Schema definitions for query analysis
# @note: Intent detection uses pattern matching; can be enhanced with LLM for complex queries

from __future__ import annotations

import re
import logging
from enum import Enum
from typing import List, Optional, Set

from pydantic import BaseModel, Field


# ============================================================================
# LOGGING
# ============================================================================

logger = logging.getLogger(__name__)


# ============================================================================
# CONFIGURATION
# ============================================================================

# Common stop words to filter from key terms
STOP_WORDS: Set[str] = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "must", "shall", "can", "need", "dare",
    "ought", "used", "to", "of", "in", "for", "on", "with", "at", "by",
    "from", "up", "about", "into", "over", "after", "beneath", "under",
    "above", "and", "but", "or", "nor", "so", "yet", "both", "either",
    "neither", "not", "only", "own", "same", "than", "too", "very",
    "just", "also", "now", "here", "there", "when", "where", "why",
    "how", "all", "each", "every", "both", "few", "more", "most",
    "other", "some", "such", "no", "any", "if", "then", "because",
    "as", "until", "while", "although", "though", "after", "before",
    "i", "me", "my", "myself", "we", "our", "ours", "ourselves",
    "you", "your", "yours", "yourself", "yourselves", "he", "him",
    "his", "himself", "she", "her", "hers", "herself", "it", "its",
    "itself", "they", "them", "their", "theirs", "themselves",
    "what", "which", "who", "whom", "this", "that", "these", "those",
    "am", "between", "during", "through",
}

# Minimum term length for key term extraction
MIN_TERM_LENGTH = 2

# Intent detection patterns (regex patterns mapped to intents)
INTENT_PATTERNS = {
    "factual": [
        r"^what\s+is\b",
        r"^what\s+are\b",
        r"^who\s+is\b",
        r"^who\s+are\b",
        r"^when\s+was\b",
        r"^when\s+did\b",
        r"^where\s+is\b",
        r"^define\b",
        r"^definition\s+of\b",
    ],
    "conceptual": [
        r"^explain\b",
        r"^describe\b",
        r"^why\s+is\b",
        r"^why\s+are\b",
        r"^why\s+do\b",
        r"^why\s+does\b",
        r"^what\s+causes\b",
        r"^how\s+does\b.*work",
        r"^understand\b",
    ],
    "comparative": [
        r"^compare\b",
        r"^contrast\b",
        r"^difference\s+between\b",
        r"^differences\s+between\b",
        r"^similarities\s+between\b",
        r"\bvs\.?\b",
        r"\bversus\b",
        r"\bcompared\s+to\b",
        r"\bdifference\b.*\band\b",
    ],
    "procedural": [
        r"^how\s+to\b",
        r"^how\s+do\s+i\b",
        r"^how\s+can\s+i\b",
        r"^steps\s+to\b",
        r"^guide\s+to\b",
        r"^process\s+of\b",
        r"^procedure\s+for\b",
        r"^method\s+for\b",
    ],
    "exploratory": [
        r"^tell\s+me\s+about\b",
        r"^what\s+do\s+you\s+know\b",
        r"^information\s+about\b",
        r"^overview\s+of\b",
        r"^summary\s+of\b",
        r"^introduction\s+to\b",
    ],
}

# Constraint detection patterns
CONSTRAINT_PATTERNS = {
    "topic": [
        r"\babout\s+(.+?)(?:\s+and|\s+or|$)",
        r"\bregarding\s+(.+?)(?:\s+and|\s+or|$)",
        r"\bconcerning\s+(.+?)(?:\s+and|\s+or|$)",
    ],
    "scope": [
        r"\bin\s+(?:the\s+)?context\s+of\s+(.+?)(?:\s+and|\s+or|$)",
        r"\bwithin\s+(.+?)(?:\s+and|\s+or|$)",
        r"\bfor\s+(.+?)(?:\s+and|\s+or|$)",
    ],
    "time": [
        r"\bin\s+(\d{4})\b",
        r"\bsince\s+(\d{4})\b",
        r"\bbefore\s+(\d{4})\b",
        r"\bafter\s+(\d{4})\b",
        r"\b(recent|latest|current|modern)\b",
    ],
}


# ============================================================================
# DATA MODELS
# ============================================================================


class QueryIntent(str, Enum):
    """Enumeration of query intent types."""

    FACTUAL = "factual"  # "What is X?"
    CONCEPTUAL = "conceptual"  # "Explain Y"
    COMPARATIVE = "comparative"  # "Compare X and Y"
    PROCEDURAL = "procedural"  # "How to Z?"
    EXPLORATORY = "exploratory"  # "Tell me about X"
    UNKNOWN = "unknown"  # Default when no pattern matches


class QueryConstraint(BaseModel):
    """Constraint extracted from query."""

    type: str = Field(description="Constraint type: topic, time, scope")
    value: str = Field(description="Constraint value")


class QueryAnalysis(BaseModel):
    """Complete analysis of a search query."""

    original_query: str = Field(description="Original query text")
    normalized_query: str = Field(description="Normalized/cleaned query")
    intent: QueryIntent = Field(
        default=QueryIntent.UNKNOWN,
        description="Detected query intent",
    )
    key_terms: List[str] = Field(
        default_factory=list,
        description="Key terms extracted from query",
    )
    constraints: List[QueryConstraint] = Field(
        default_factory=list,
        description="Constraints identified in query",
    )
    suggested_expansion: bool = Field(
        default=True,
        description="Whether query expansion is recommended",
    )
    confidence: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Confidence in the analysis",
    )


# ============================================================================
# QUERY ANALYZER CLASS
# ============================================================================


class QueryAnalyzer:
    """
    Analyzes search queries to extract intent, key terms, and constraints.

    Supports query expansion decisions and future answer synthesis by
    understanding what type of question is being asked.

    Features:
    - Intent detection (factual, conceptual, comparative, procedural, exploratory)
    - Key term extraction with stop word filtering
    - Constraint identification (topic, time, scope)
    - Query normalization and cleaning

    Example:
        analyzer = QueryAnalyzer()

        analysis = analyzer.analyze("What is the difference between CNN and RNN?")
        # QueryAnalysis(
        #     intent=QueryIntent.COMPARATIVE,
        #     key_terms=["difference", "CNN", "RNN"],
        #     suggested_expansion=True
        # )

        analysis = analyzer.analyze("How to implement backpropagation?")
        # QueryAnalysis(
        #     intent=QueryIntent.PROCEDURAL,
        #     key_terms=["implement", "backpropagation"],
        #     suggested_expansion=True
        # )
    """

    def __init__(self):
        """Initialize QueryAnalyzer with compiled regex patterns."""
        # Compile intent patterns for efficiency
        self._intent_patterns = {}
        for intent, patterns in INTENT_PATTERNS.items():
            self._intent_patterns[intent] = [
                re.compile(p, re.IGNORECASE) for p in patterns
            ]

        # Compile constraint patterns
        self._constraint_patterns = {}
        for constraint_type, patterns in CONSTRAINT_PATTERNS.items():
            self._constraint_patterns[constraint_type] = [
                re.compile(p, re.IGNORECASE) for p in patterns
            ]

        logger.info("QueryAnalyzer initialized")

    def analyze(self, query: str) -> QueryAnalysis:
        """
        Perform complete analysis of a search query.

        Args:
            query: Raw query text

        Returns:
            QueryAnalysis with intent, key terms, and constraints
        """
        if not query or not query.strip():
            return QueryAnalysis(
                original_query=query or "",
                normalized_query="",
                intent=QueryIntent.UNKNOWN,
                key_terms=[],
                constraints=[],
                suggested_expansion=False,
                confidence=0.0,
            )

        # Normalize query
        normalized = self._normalize_query(query)

        # Detect intent
        intent, intent_confidence = self.determine_intent(query)

        # Extract key terms
        key_terms = self.extract_key_terms(query)

        # Identify constraints
        constraints = self.identify_constraints(query)

        # Determine if expansion is recommended
        # Short queries and exploratory/conceptual queries benefit from expansion
        suggested_expansion = self._should_expand(query, intent, key_terms)

        # Calculate overall confidence
        confidence = self._calculate_confidence(
            intent, intent_confidence, key_terms, constraints
        )

        analysis = QueryAnalysis(
            original_query=query,
            normalized_query=normalized,
            intent=intent,
            key_terms=key_terms,
            constraints=constraints,
            suggested_expansion=suggested_expansion,
            confidence=confidence,
        )

        logger.debug(
            f"Query analysis: intent={intent.value}, "
            f"terms={len(key_terms)}, expand={suggested_expansion}"
        )

        return analysis

    def extract_key_terms(self, query: str) -> List[str]:
        """
        Extract key terms from query, filtering stop words.

        Args:
            query: Raw query text

        Returns:
            List of key terms in order of appearance
        """
        if not query:
            return []

        # Normalize and tokenize
        normalized = self._normalize_query(query)

        # Split on whitespace and punctuation
        tokens = re.split(r"[\s,;:.!?\-_/\\]+", normalized)

        # Filter stop words and short terms
        key_terms = []
        seen = set()

        for token in tokens:
            token_lower = token.lower()

            # Skip stop words, short terms, and duplicates
            if (
                token_lower in STOP_WORDS
                or len(token) < MIN_TERM_LENGTH
                or token_lower in seen
            ):
                continue

            # Skip pure numbers (but keep alphanumeric like "CNN", "RNN")
            if token.isdigit():
                continue

            seen.add(token_lower)
            key_terms.append(token)

        return key_terms

    def determine_intent(self, query: str) -> tuple[QueryIntent, float]:
        """
        Determine the intent of a query.

        Args:
            query: Raw query text

        Returns:
            Tuple of (QueryIntent, confidence)
        """
        if not query:
            return QueryIntent.UNKNOWN, 0.0

        query_lower = query.lower().strip()

        # Check each intent's patterns
        for intent_name, patterns in self._intent_patterns.items():
            for pattern in patterns:
                if pattern.search(query_lower):
                    intent = QueryIntent(intent_name)
                    # Higher confidence for early match (more specific patterns first)
                    confidence = 0.85
                    return intent, confidence

        # Default to exploratory for questions, unknown for others
        if query_lower.endswith("?"):
            return QueryIntent.EXPLORATORY, 0.5

        return QueryIntent.UNKNOWN, 0.3

    def identify_constraints(self, query: str) -> List[QueryConstraint]:
        """
        Identify constraints in the query (topic, time, scope).

        Args:
            query: Raw query text

        Returns:
            List of QueryConstraint objects
        """
        if not query:
            return []

        constraints = []

        for constraint_type, patterns in self._constraint_patterns.items():
            for pattern in patterns:
                matches = pattern.findall(query)
                for match in matches:
                    if match and isinstance(match, str) and match.strip():
                        constraints.append(
                            QueryConstraint(
                                type=constraint_type,
                                value=match.strip(),
                            )
                        )

        return constraints

    def _normalize_query(self, query: str) -> str:
        """
        Normalize query text for processing.

        - Lowercase
        - Remove extra whitespace
        - Remove special characters (keep alphanumeric and basic punctuation)
        """
        if not query:
            return ""

        # Convert to lowercase
        normalized = query.lower().strip()

        # Remove extra whitespace
        normalized = re.sub(r"\s+", " ", normalized)

        # Keep alphanumeric, spaces, and basic punctuation
        normalized = re.sub(r"[^\w\s.,!?'\"-]", " ", normalized)

        # Remove extra whitespace again after substitution
        normalized = re.sub(r"\s+", " ", normalized).strip()

        return normalized

    def _should_expand(
        self,
        query: str,
        intent: QueryIntent,
        key_terms: List[str],
    ) -> bool:
        """
        Determine if query expansion is recommended.

        Expansion is helpful for:
        - Short queries (< 5 terms)
        - Conceptual and exploratory queries
        - Queries without specific entities
        """
        # Short queries benefit from expansion
        if len(key_terms) <= 3:
            return True

        # Conceptual and exploratory queries benefit from expansion
        if intent in (
            QueryIntent.CONCEPTUAL,
            QueryIntent.EXPLORATORY,
            QueryIntent.COMPARATIVE,
        ):
            return True

        # Procedural queries may need context from related concepts
        if intent == QueryIntent.PROCEDURAL:
            return True

        # Factual queries with specific terms may not need expansion
        if intent == QueryIntent.FACTUAL and len(key_terms) >= 4:
            return False

        # Default to expanding
        return True

    def _calculate_confidence(
        self,
        intent: QueryIntent,
        intent_confidence: float,
        key_terms: List[str],
        constraints: List[QueryConstraint],
    ) -> float:
        """
        Calculate overall confidence in the analysis.

        Considers:
        - Intent detection confidence
        - Number of key terms found
        - Whether constraints were identified
        """
        confidence = intent_confidence

        # Boost confidence if we found meaningful key terms
        if len(key_terms) >= 2:
            confidence += 0.1

        # Boost confidence if constraints were identified
        if constraints:
            confidence += 0.05

        # Reduce confidence for unknown intent
        if intent == QueryIntent.UNKNOWN:
            confidence -= 0.2

        # Clamp to [0, 1]
        return max(0.0, min(1.0, confidence))


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================


def create_query_analyzer() -> QueryAnalyzer:
    """
    Factory function to create QueryAnalyzer.

    Returns:
        Configured QueryAnalyzer instance
    """
    return QueryAnalyzer()
