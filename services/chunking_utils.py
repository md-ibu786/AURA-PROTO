# chunking_utils.py
# Reusable text chunking utilities for KG processing

# Utility functions for token counting, sentence splitting, and text chunking.
# Uses tiktoken for accurate GPT-4 compatible token counting.
# Stateless module - no dependencies on Neo4j or embedding services.

# @see: api/kg_processor.py - Main consumer of these utilities
# @note: Falls back to whitespace tokenization if tiktoken unavailable

"""
Text chunking utilities for AURA-NOTES-MANAGER knowledge graph processing.

Provides stateless utility functions for:
- Token counting (tiktoken with cl100k_base encoding)
- Sentence splitting with abbreviation handling
- Token-aware text chunking with overlap
- Text normalization (whitespace, unicode)

Ported from AURA-CHAT/backend/document_processor.py for consistency across
both applications in the AURA monorepo.
"""

from typing import List, Optional
import re
import unicodedata

# Module-level tiktoken encoder (lazy initialization)
_encoding = None


def _get_encoding():
    """
    Get or initialize the tiktoken encoder.

    Returns:
        tiktoken.Encoding or None if tiktoken unavailable
    """
    global _encoding
    if _encoding is None:
        try:
            import tiktoken

            _encoding = tiktoken.get_encoding("cl100k_base")
        except ImportError:
            _encoding = False  # Mark as unavailable
    return _encoding if _encoding else None


def count_tokens(text: str, model: str = "gpt-4") -> int:
    """
    Count tokens using tiktoken. Falls back to whitespace if unavailable.

    Uses cl100k_base encoding which is compatible with GPT-4 and modern
    OpenAI/Google models. Falls back to whitespace-based word count if
    tiktoken is not installed.

    Args:
        text: Text to count tokens for
        model: Model name (unused, kept for API compatibility)

    Returns:
        Token count (int)

    Example:
        >>> count_tokens("Hello, world!")
        4
        >>> count_tokens("")
        0
    """
    if not text:
        return 0

    encoding = _get_encoding()
    if encoding:
        return len(encoding.encode(text))

    # Fallback: whitespace tokenization (approximate)
    return len(text.split())


def split_into_sentences(text: str) -> List[str]:
    """
    Split text into sentences using regex patterns.

    Handles common abbreviations (Dr., Mr., Mrs., Ms., Prof., etc.) and
    numeric patterns (e.g., "1.5", "3.14") to avoid false sentence breaks.
    Supports multiple sentence-ending punctuation: . ! ?

    Args:
        text: Text to split into sentences

    Returns:
        List of sentence strings (empty sentences filtered out)

    Example:
        >>> split_into_sentences("Hello. World!")
        ['Hello.', 'World!']
        >>> split_into_sentences("Dr. Smith went home. He was tired.")
        ['Dr. Smith went home.', 'He was tired.']
    """
    if not text:
        return []

    # Common abbreviations that shouldn't end sentences
    abbreviations = {
        "dr",
        "mr",
        "mrs",
        "ms",
        "prof",
        "sr",
        "jr",
        "vs",
        "etc",
        "inc",
        "ltd",
        "corp",
        "eg",
        "ie",
        "al",
        "fig",
        "vol",
        "no",
        "pp",
        "ed",
        "rev",
        "gen",
        "col",
        "lt",
        "capt",
        "sgt",
        "ph",
        "st",
        "ave",
        "blvd",
    }

    sentences = []
    current = []
    words = text.split()

    for i, word in enumerate(words):
        current.append(word)

        # Check if word ends with sentence punctuation
        if re.search(r"[.!?]$", word):
            # Get the base word without punctuation for abbreviation check
            base_word = re.sub(r"[.!?,;:]+$", "", word).lower()

            # Skip if it's a known abbreviation
            if base_word in abbreviations:
                continue

            # Skip if it looks like a number (e.g., "3.14", "1.5")
            if re.match(r"^\d+\.\d*$", word.rstrip(".!?")):
                continue

            # Skip if next word starts with lowercase (likely not sentence end)
            if i + 1 < len(words):
                next_word = words[i + 1]
                # If next word starts with lowercase and current ends with '.'
                # it might be an abbreviation we missed
                if word.endswith(".") and next_word[0].islower():
                    continue

            # This is a sentence boundary
            sentence = " ".join(current)
            sentences.append(sentence)
            current = []

    # Handle remaining text (no final punctuation)
    if current:
        sentences.append(" ".join(current))

    # Filter empty sentences and return
    return [s.strip() for s in sentences if s.strip()]


def chunk_by_tokens(text: str, max_tokens: int, overlap: int = 0) -> List[str]:
    """
    Token-aware chunking with optional overlap.

    Splits text into chunks of approximately max_tokens size, with optional
    overlap between consecutive chunks for context continuity. Uses word
    boundaries to avoid splitting mid-word.

    Args:
        text: Text to chunk
        max_tokens: Maximum tokens per chunk
        overlap: Number of tokens to overlap between chunks (default: 0)

    Returns:
        List of chunk strings

    Example:
        >>> chunks = chunk_by_tokens("Hello world. How are you?", 3, 1)
        >>> len(chunks) >= 2
        True
    """
    if not text or max_tokens <= 0:
        return []

    words = text.split()
    if not words:
        return []

    chunks = []
    start = 0

    while start < len(words):
        # Find end position for this chunk
        end = start
        current_tokens = 0

        while end < len(words):
            word_tokens = count_tokens(words[end])
            if current_tokens + word_tokens > max_tokens and end > start:
                break
            current_tokens += word_tokens
            end += 1

        # Create chunk from words[start:end]
        chunk_text = " ".join(words[start:end])
        chunks.append(chunk_text)

        # Move start position, accounting for overlap
        if overlap > 0 and end < len(words):
            # Calculate how many words to keep for overlap
            overlap_words = 0
            overlap_tokens = 0
            for i in range(end - 1, start - 1, -1):
                word_tokens = count_tokens(words[i])
                if overlap_tokens + word_tokens > overlap:
                    break
                overlap_tokens += word_tokens
                overlap_words += 1

            start = end - overlap_words
        else:
            start = end

        # Safety check to prevent infinite loop
        if start == end and end < len(words):
            start = end + 1

    return chunks


def normalize_text(text: str) -> str:
    """
    Normalize whitespace and characters.

    Performs the following normalizations:
    - Unicode normalization (NFKC)
    - Collapse multiple whitespace to single space
    - Strip leading/trailing whitespace
    - Replace various unicode spaces with regular space
    - Remove control characters (except newlines and tabs)

    Args:
        text: Text to normalize

    Returns:
        Normalized text string

    Example:
        >>> normalize_text("  Hello   world  ")
        'Hello world'
        >>> normalize_text("Hello\\n\\n\\nWorld")
        'Hello World'
    """
    if not text:
        return ""

    # Unicode normalization (NFKC: compatibility decomposition + canonical composition)
    text = unicodedata.normalize("NFKC", text)

    # Replace various unicode whitespace with regular space
    # This includes non-breaking space, em space, en space, etc.
    text = re.sub(r"[\u00a0\u2000-\u200b\u2028\u2029\u202f\u205f\u3000]", " ", text)

    # Remove control characters except newlines and tabs
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)

    # Collapse multiple newlines to single space (for chunking purposes)
    text = re.sub(r"\n+", " ", text)

    # Collapse multiple tabs to single space
    text = re.sub(r"\t+", " ", text)

    # Collapse multiple spaces to single space
    text = re.sub(r" +", " ", text)

    # Strip leading/trailing whitespace
    text = text.strip()

    return text
