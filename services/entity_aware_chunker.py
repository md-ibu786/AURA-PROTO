# entity_aware_chunker.py
# Entity-aware chunker that preserves entity context boundaries for KG processing

# Implements the entity-aware chunking algorithm from AURA-CHAT, including context
# extraction, context merging, oversized chunk splitting, and gap filling.
# Provides a lightweight wrapper to generate hierarchical chunks for compatibility
# with downstream services that expect section-aware chunking output.

# @see: services/llm_entity_extractor.py - Entity extraction inputs
# @see: services/chunking_utils.py - Token counting utilities
# @note: Falls back to token-based chunking when no entities are provided

from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Any, Dict, List, Tuple

from services.chunking_utils import count_tokens

logger = logging.getLogger(__name__)

# Configuration defaults (aligned with AURA-CHAT/backend/utils/config.py)
ENTITY_CONTEXT_WINDOW = 400
ENTITY_MERGE_DISTANCE = 500
MIN_CHUNK_TOKENS = 200
MAX_CHUNK_TOKENS = 1200
GAP_FILL_THRESHOLD = 1000
CHUNK_SIZE = 800
CHUNK_OVERLAP = 200


@dataclass
class EntityContext:
    entity_id: str
    entity_name: str
    start: int
    end: int
    context_start: int
    context_end: int
    text: str


@dataclass
class Chunk:
    text: str
    chunk_id: str
    section_path: List[str]
    entities_mentioned: List[str]


class EntityAwareChunker:
    def __init__(self, chunker_config: Dict[str, Any] | None = None):
        config = chunker_config or {}
        self.context_window = config.get("ENTITY_CONTEXT_WINDOW", ENTITY_CONTEXT_WINDOW)
        self.merge_distance = config.get("ENTITY_MERGE_DISTANCE", ENTITY_MERGE_DISTANCE)
        self.min_chunk_tokens = config.get("MIN_CHUNK_TOKENS", MIN_CHUNK_TOKENS)
        self.max_chunk_tokens = config.get("MAX_CHUNK_TOKENS", MAX_CHUNK_TOKENS)
        self.gap_fill_threshold = config.get("GAP_FILL_THRESHOLD", GAP_FILL_THRESHOLD)
        self.chunk_size = config.get("CHUNK_SIZE", CHUNK_SIZE)
        self.chunk_overlap = config.get("CHUNK_OVERLAP", CHUNK_OVERLAP)
        self._encoding = None

        logger.info(
            "Initialized EntityAwareChunker: context_window=%s, merge_distance=%s, "
            "min_tokens=%s, max_tokens=%s",
            self.context_window,
            self.merge_distance,
            self.min_chunk_tokens,
            self.max_chunk_tokens,
        )

    def chunk_document(
        self, text: str, entities: Dict[str, List[Dict[str, Any]]]
    ) -> List[Dict[str, Any]]:
        if not text or not text.strip():
            logger.warning("Empty text provided for chunking")
            return []

        all_entities = self._flatten_entities(entities)

        if not all_entities:
            logger.info("No entities found, falling back to token-based chunking")
            return self._fallback_chunking(text)

        logger.info("Processing %s entities for chunking", len(all_entities))

        entity_contexts = self._extract_entity_contexts(text, all_entities)

        if not entity_contexts:
            logger.warning(
                "No entity contexts extracted, falling back to token-based chunking"
            )
            return self._fallback_chunking(text)

        merged_contexts = self._merge_contexts(entity_contexts, text)
        chunks = self._create_chunks(text, merged_contexts)
        chunks = self._fill_gaps(text, chunks, all_entities, entity_contexts)

        self._validate_chunks(chunks)

        logger.info("Created %s entity-aware chunks", len(chunks))
        return chunks

    def chunk_text_hierarchical(self, text: str, document_id: str) -> List[Chunk]:
        sections = self._extract_sections(text)
        chunks: List[Chunk] = []
        chunk_index = 0

        for section_path, section_text in sections:
            section_chunks = self._chunk_section(
                section_text=section_text,
                section_path=section_path,
                document_id=document_id,
                start_index=chunk_index,
            )
            chunks.extend(section_chunks)
            chunk_index += len(section_chunks)

        return chunks

    def _flatten_entities(
        self, entities: Dict[str, List[Dict[str, Any]]]
    ) -> List[Dict[str, Any]]:
        all_entities: List[Dict[str, Any]] = []
        for entity_list in entities.values():
            all_entities.extend(entity_list)
        return all_entities

    def _extract_entity_contexts(
        self, text: str, entities: List[Dict[str, Any]]
    ) -> List[EntityContext]:
        contexts = []
        text_lower = text.lower()

        for entity in entities:
            entity_name = entity.get("name", "").strip()
            entity_id = entity.get("id", "")

            if not entity_name or not entity_id:
                continue

            entity_name_lower = entity_name.lower()
            start = 0

            while True:
                pos = text_lower.find(entity_name_lower, start)
                if pos == -1:
                    break

                end = pos + len(entity_name)
                context_start = max(0, pos - self.context_window)
                context_end = min(len(text), end + self.context_window)

                context_start, context_end = self._expand_to_sentences(
                    text, context_start, context_end
                )

                context_text = text[context_start:context_end]
                contexts.append(
                    EntityContext(
                        entity_id=entity_id,
                        entity_name=entity_name,
                        start=pos,
                        end=end,
                        context_start=context_start,
                        context_end=context_end,
                        text=context_text,
                    )
                )

                start = end

        logger.debug("Extracted %s entity contexts", len(contexts))
        return contexts

    def _expand_to_sentences(self, text: str, start: int, end: int) -> Tuple[int, int]:
        sentence_endings = [".", "!", "?", "\n"]

        while start > 0 and text[start - 1] not in sentence_endings:
            start -= 1

        while end < len(text) and text[end] not in sentence_endings:
            end += 1

        if end < len(text) and text[end] in sentence_endings:
            end += 1

        return start, end

    def _merge_contexts(
        self, contexts: List[EntityContext], text: str
    ) -> List[Dict[str, Any]]:
        if not contexts:
            return []

        contexts.sort(key=lambda ctx: ctx.context_start)
        merged = []
        current_contexts = [contexts[0]]

        for ctx in contexts[1:]:
            last_ctx = current_contexts[-1]
            gap_in_tokens = self._token_count(
                text[last_ctx.context_end : ctx.context_start]
            )
            entity_gap_tokens = 0
            if ctx.start > last_ctx.end:
                entity_gap_tokens = self._token_count(text[last_ctx.end : ctx.start])

            if (
                gap_in_tokens <= self.merge_distance
                and entity_gap_tokens <= self.merge_distance
            ):
                current_contexts.append(ctx)
            else:
                merged.append(self._create_merged_context(current_contexts))
                current_contexts = [ctx]

        if current_contexts:
            merged.append(self._create_merged_context(current_contexts))

        logger.debug("Merged %s contexts into %s chunks", len(contexts), len(merged))
        return merged

    def _create_merged_context(self, contexts: List[EntityContext]) -> Dict[str, Any]:
        if not contexts:
            return {}

        start = min(ctx.context_start for ctx in contexts)
        end = max(ctx.context_end for ctx in contexts)

        entity_ids = list({ctx.entity_id for ctx in contexts})
        entity_names = list({ctx.entity_name for ctx in contexts})
        entity_map = {ctx.entity_name: ctx.entity_id for ctx in contexts}

        primary_entity = max(
            contexts, key=lambda ctx: ctx.context_end - ctx.context_start
        ).entity_id

        return {
            "start": start,
            "end": end,
            "entity_ids": entity_ids,
            "entity_names": entity_names,
            "entity_map": entity_map,
            "primary_entity": primary_entity,
        }

    def _create_chunks(
        self, text: str, merged_contexts: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        chunks = []
        chunk_index = 0

        for ctx in merged_contexts:
            chunk_text = text[ctx["start"] : ctx["end"]].strip()

            if not chunk_text:
                continue

            token_count = self._token_count(chunk_text)

            if token_count < self.min_chunk_tokens:
                expanded_start, expanded_end = self._expand_chunk(
                    text, ctx["start"], ctx["end"], self.min_chunk_tokens
                )
                chunk_text = text[expanded_start:expanded_end].strip()
                token_count = self._token_count(chunk_text)

            if token_count > self.max_chunk_tokens:
                new_chunks = self._split_large_chunk(chunk_text, ctx, chunk_index)
                chunks.extend(new_chunks)
                chunk_index += len(new_chunks)
            else:
                entity_ids, entity_names, primary_entity = self._filter_entities_for_text(
                    chunk_text,
                    ctx.get("entity_map", {}),
                    ctx.get("primary_entity", ""),
                )
                chunks.append(
                    {
                        "index": chunk_index,
                        "text": chunk_text,
                        "token_count": token_count,
                        "entities": entity_ids,
                        "entity_names": entity_names,
                        "primary_entity": primary_entity,
                        "position": {"start": ctx["start"], "end": ctx["end"]},
                    }
                )
                chunk_index += 1

        return chunks

    def _expand_chunk(
        self, text: str, start: int, end: int, target_tokens: int
    ) -> Tuple[int, int]:
        current_tokens = self._token_count(text[start:end])

        while current_tokens < target_tokens and (start > 0 or end < len(text)):
            expanded = False

            if start > 0:
                prev_start = max(0, start - 100)
                added_tokens = self._token_count(text[prev_start:start])
                if current_tokens + added_tokens <= self.max_chunk_tokens:
                    start = prev_start
                    current_tokens += added_tokens
                    expanded = True

            if end < len(text):
                next_end = min(len(text), end + 100)
                added_tokens = self._token_count(text[end:next_end])
                if current_tokens + added_tokens <= self.max_chunk_tokens:
                    end = next_end
                    current_tokens += added_tokens
                    expanded = True

            if not expanded:
                break

        start, end = self._expand_to_sentences(text, start, end)
        return start, end

    def _split_large_chunk(
        self, text: str, ctx: Dict[str, Any], start_index: int
    ) -> List[Dict[str, Any]]:
        chunks = []
        paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
        current_text: List[str] = []
        current_tokens: List[int] = []
        chunk_index = start_index
        overlap = 50

        def _save_chunk(
            current_text: List[str], current_tokens: List[int], chunk_index: int
        ) -> int:
            if not current_tokens:
                return chunk_index

            chunk_text = " ".join(current_text)
            actual_tokens = self._token_count(chunk_text)
            if actual_tokens > self.max_chunk_tokens:
                words = chunk_text.split()
                sub_chunks = self._split_words_to_chunks(words, ctx, chunk_index)
                chunks.extend(sub_chunks)
                return chunk_index + len(sub_chunks)

            entity_ids, entity_names, primary_entity = self._filter_entities_for_text(
                chunk_text,
                ctx.get("entity_map", {}),
                ctx.get("primary_entity", ""),
            )
            chunks.append(
                {
                    "index": chunk_index,
                    "text": chunk_text,
                    "token_count": actual_tokens,
                    "entities": entity_ids,
                    "entity_names": entity_names,
                    "primary_entity": primary_entity,
                    "position": {"start": ctx["start"], "end": ctx["end"]},
                }
            )
            return chunk_index + 1

        for para in paragraphs:
            para_tokens = self._token_count(para)

            if para_tokens > self.max_chunk_tokens:
                if current_tokens:
                    chunk_index = _save_chunk(current_text, current_tokens, chunk_index)
                    current_text = []
                    current_tokens = []

                words = para.split()
                word_chunks = self._split_words_to_chunks(words, ctx, chunk_index)
                chunks.extend(word_chunks)
                chunk_index += len(word_chunks)

                if word_chunks:
                    last_chunk_words = word_chunks[-1]["text"].split()[-20:]
                    current_text = last_chunk_words
                    current_tokens = [self._token_count(" ".join(last_chunk_words))]
                continue

            if self._token_count(" ".join(current_text)) + para_tokens > self.max_chunk_tokens:
                if current_tokens:
                    chunk_index = _save_chunk(current_text, current_tokens, chunk_index)

                overlap_text: List[str] = []
                overlap_tokens_count = 0

                for prev_para in reversed(current_text):
                    prev_tokens = self._token_count(prev_para)
                    if overlap_tokens_count + prev_tokens > overlap:
                        break
                    overlap_text.insert(0, prev_para)
                    overlap_tokens_count += prev_tokens

                current_text = overlap_text
                current_tokens = [self._token_count(" ".join(overlap_text))] if overlap_text else []

            current_text.append(para)
            current_tokens.append(para_tokens)

        if current_tokens:
            _save_chunk(current_text, current_tokens, chunk_index)

        return chunks

    def _split_words_to_chunks(
        self, words: List[str], ctx: Dict[str, Any], start_index: int
    ) -> List[Dict[str, Any]]:
        chunks = []
        chunk_index = start_index
        current_words: List[str] = []
        current_token_count = 0
        overlap_words = 20

        for word in words:
            word_tokens = self._token_count(f"{word} ")

            if current_token_count + word_tokens > self.max_chunk_tokens:
                if current_words:
                    chunk_text = " ".join(current_words)
                    entity_ids, entity_names, primary_entity = self._filter_entities_for_text(
                        chunk_text,
                        ctx.get("entity_map", {}),
                        ctx.get("primary_entity", ""),
                    )
                    chunks.append(
                        {
                            "index": chunk_index,
                            "text": chunk_text,
                            "token_count": current_token_count,
                            "entities": entity_ids,
                            "entity_names": entity_names,
                            "primary_entity": primary_entity,
                            "position": {"start": ctx["start"], "end": ctx["end"]},
                        }
                    )
                    chunk_index += 1

                    keep_words = (
                        current_words[-overlap_words:]
                        if len(current_words) > overlap_words
                        else []
                    )
                    current_words = keep_words
                    current_token_count = (
                        self._token_count(" ".join(keep_words)) if keep_words else 0
                    )

            current_words.append(word)
            current_token_count += word_tokens

        if current_words:
            chunk_text = " ".join(current_words)
            entity_ids, entity_names, primary_entity = self._filter_entities_for_text(
                chunk_text,
                ctx.get("entity_map", {}),
                ctx.get("primary_entity", ""),
            )
            chunks.append(
                {
                    "index": chunk_index,
                    "text": chunk_text,
                    "token_count": self._token_count(chunk_text),
                    "entities": entity_ids,
                    "entity_names": entity_names,
                    "primary_entity": primary_entity,
                    "position": {"start": ctx["start"], "end": ctx["end"]},
                }
            )

        return chunks

    def _fill_gaps(
        self,
        text: str,
        chunks: List[Dict[str, Any]],
        entities: List[Dict[str, Any]],
        contexts: List[EntityContext] | None = None,
    ) -> List[Dict[str, Any]]:
        if not chunks:
            return self._fallback_chunking(text)

        chunks.sort(key=lambda chunk: chunk["position"]["start"])

        gaps = []
        last_end = 0

        for chunk in chunks:
            gap_start = last_end
            gap_end = chunk["position"]["start"]

            if gap_end > gap_start:
                gap_text = text[gap_start:gap_end].strip()
                if gap_text:
                    gap_tokens = self._token_count(gap_text)
                    if gap_tokens >= self.gap_fill_threshold:
                        gaps.append(
                            {
                                "start": gap_start,
                                "end": gap_end,
                                "text": gap_text,
                                "tokens": gap_tokens,
                            }
                        )

            last_end = max(last_end, chunk["position"]["end"])

        if last_end < len(text):
            gap_text = text[last_end:].strip()
            if gap_text:
                gap_tokens = self._token_count(gap_text)
                if gap_tokens >= self.gap_fill_threshold:
                    gaps.append(
                        {
                            "start": last_end,
                            "end": len(text),
                            "text": gap_text,
                            "tokens": gap_tokens,
                        }
                    )

        if not gaps and contexts:
            entity_gap_threshold = max(10, self.gap_fill_threshold // 2)
            contexts_sorted = sorted(contexts, key=lambda ctx: ctx.start)
            for prev_ctx, next_ctx in zip(contexts_sorted, contexts_sorted[1:]):
                if next_ctx.start <= prev_ctx.end:
                    continue
                gap_text = text[prev_ctx.end : next_ctx.start].strip()
                if not gap_text:
                    continue
                gap_tokens = self._token_count(gap_text)
                if gap_tokens >= entity_gap_threshold:
                    gaps.append(
                        {
                            "start": prev_ctx.end,
                            "end": next_ctx.start,
                            "text": gap_text,
                            "tokens": gap_tokens,
                        }
                    )

        if gaps:
            background_chunks = self._create_background_chunks(text, gaps, entities)
            chunks.extend(background_chunks)
            chunks.sort(key=lambda chunk: chunk["position"]["start"])
            chunks = [
                chunk._replace(index=i)
                if hasattr(chunk, "_replace")
                else {**chunk, "index": i}
                for i, chunk in enumerate(chunks)
            ]

        return chunks

    def _create_background_chunks(
        self, text: str, gaps: List[Dict[str, Any]], entities: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        background_chunks = []
        chunk_index = 0

        for gap in gaps:
            gap_chunks = self._chunk_text_with_size(gap["text"])

            for i, chunk_text in enumerate(gap_chunks):
                token_count = self._token_count(chunk_text)
                start = gap["start"] + i * (len(gap["text"]) // len(gap_chunks))
                end = start + len(chunk_text)

                nearby_entities = self._find_nearby_entities(text, entities, start, end, 500)
                entity_map = {entity["name"]: entity["id"] for entity in nearby_entities}
                entity_ids, entity_names, primary_entity = self._filter_entities_for_text(
                    chunk_text, entity_map, ""
                )

                background_chunks.append(
                    {
                        "index": chunk_index,
                        "text": chunk_text,
                        "token_count": token_count,
                        "entities": entity_ids,
                        "entity_names": entity_names,
                        "primary_entity": primary_entity,
                        "position": {"start": start, "end": end},
                    }
                )
                chunk_index += 1

        return background_chunks

    def _find_nearby_entities(
        self,
        text: str,
        entities: List[Dict[str, Any]],
        chunk_start: int,
        chunk_end: int,
        threshold: int,
    ) -> List[Dict[str, Any]]:
        nearby = []
        text_lower = text.lower()

        for entity in entities:
            entity_name = entity.get("name", "").strip().lower()
            if not entity_name:
                continue

            pos = text_lower.find(entity_name, max(0, chunk_start - threshold))
            if pos != -1 and pos < chunk_end + threshold:
                nearby.append(entity)

        return nearby

    def _filter_entities_for_text(
        self, chunk_text: str, entity_map: Dict[str, str], primary_entity: str
    ) -> Tuple[List[str], List[str], str]:
        text_lower = chunk_text.lower()
        filtered_names = [
            name for name in entity_map.keys() if name and name.lower() in text_lower
        ]
        filtered_ids = [entity_map[name] for name in filtered_names]

        if primary_entity and primary_entity not in filtered_ids:
            primary_entity = filtered_ids[0] if filtered_ids else ""

        return filtered_ids, filtered_names, primary_entity

    def _chunk_text_with_size(self, text: str) -> List[str]:
        target_size = 600
        overlap = 100

        paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
        chunks = []
        current_text: List[str] = []
        current_tokens: List[int] = []

        for para in paragraphs:
            para_tokens = self._token_count(para)

            if sum(current_tokens) + para_tokens > target_size + 200:
                if current_tokens:
                    chunks.append(" ".join(current_text))

                overlap_text: List[str] = []
                overlap_tokens_count = 0

                for prev_para in reversed(current_text):
                    prev_tokens = self._token_count(prev_para)
                    if overlap_tokens_count + prev_tokens > overlap:
                        break
                    overlap_text.insert(0, prev_para)
                    overlap_tokens_count += prev_tokens

                current_text = overlap_text
                current_tokens = (
                    [self._token_count(" ".join(overlap_text))] if overlap_text else []
                )

            current_text.append(para)
            current_tokens.append(para_tokens)

        if current_tokens:
            chunks.append(" ".join(current_text))

        return chunks

    def _token_count(self, text: str) -> int:
        return count_tokens(text)

    def _fallback_chunking(self, text: str) -> List[Dict[str, Any]]:
        logger.info("Using fallback token-based chunking")
        chunks = []
        paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
        current_tokens: List[int] = []
        current_text: List[str] = []
        chunk_index = 0

        for paragraph in paragraphs:
            para_tokens = self._token_count(paragraph)

            if sum(current_tokens) + para_tokens > self.chunk_size:
                if current_tokens:
                    chunk_text = " ".join(current_text)
                    chunks.append(
                        {
                            "index": chunk_index,
                            "text": chunk_text,
                            "token_count": sum(current_tokens),
                            "entities": [],
                            "entity_names": [],
                            "primary_entity": "",
                            "position": {"start": 0, "end": len(chunk_text)},
                        }
                    )
                    chunk_index += 1

                overlap_tokens = self.chunk_overlap
                overlap_paragraphs: List[str] = []
                overlap_token_count = 0

                for prev_para in reversed(current_text):
                    prev_tokens = self._token_count(prev_para)
                    if overlap_token_count + prev_tokens > overlap_tokens:
                        break
                    overlap_paragraphs.insert(0, prev_para)
                    overlap_token_count += prev_tokens

                current_text = overlap_paragraphs
                current_tokens = (
                    [self._token_count(" ".join(overlap_paragraphs))]
                    if overlap_paragraphs
                    else []
                )

            current_text.append(paragraph)
            current_tokens.append(para_tokens)

        if current_tokens:
            chunk_text = " ".join(current_text)
            chunks.append(
                {
                    "index": chunk_index,
                    "text": chunk_text,
                    "token_count": sum(current_tokens),
                    "entities": [],
                    "entity_names": [],
                    "primary_entity": "",
                    "position": {"start": 0, "end": len(chunk_text)},
                }
            )

        return chunks

    def _validate_chunks(self, chunks: List[Dict[str, Any]]) -> None:
        for i, chunk in enumerate(chunks):
            if chunk["token_count"] > self.max_chunk_tokens:
                logger.warning(
                    "Chunk %s exceeds max tokens: %s > %s",
                    i,
                    chunk["token_count"],
                    self.max_chunk_tokens,
                )
            if chunk["token_count"] < self.min_chunk_tokens:
                logger.warning(
                    "Chunk %s below min tokens: %s < %s",
                    i,
                    chunk["token_count"],
                    self.min_chunk_tokens,
                )

    def _extract_sections(self, text: str) -> List[Tuple[List[str], str]]:
        section_patterns = [
            ("#", 1),
            ("##", 2),
            ("###", 3),
            ("####", 4),
            ("#####", 5),
            ("######", 6),
        ]
        default_path = ["Document"]
        sections: List[Tuple[List[str], str]] = []
        current_path = default_path.copy()
        current_lines: List[str] = []

        def flush_section():
            if current_lines:
                sections.append((current_path.copy(), "\n".join(current_lines).strip()))

        for line in text.splitlines():
            stripped = line.strip()
            header_level = None
            header_text = ""

            for marker, level in section_patterns:
                if stripped.startswith(marker + " "):
                    header_level = level
                    header_text = stripped[len(marker) + 1 :].strip()
                    break

            if header_level is not None:
                flush_section()
                current_lines = []
                if header_level <= len(current_path):
                    current_path = current_path[: header_level - 1]
                current_path.append(header_text or f"Section {len(current_path) + 1}")
            else:
                current_lines.append(line)

        flush_section()

        if not sections and text.strip():
            sections.append((default_path, text.strip()))

        return sections

    def _chunk_section(
        self,
        section_text: str,
        section_path: List[str],
        document_id: str,
        start_index: int,
    ) -> List[Chunk]:
        if not section_text.strip():
            return []

        paragraphs = [p.strip() for p in section_text.split("\n") if p.strip()]
        chunks: List[Chunk] = []
        current_tokens = 0
        current_text: List[str] = []
        chunk_index = start_index

        for paragraph in paragraphs:
            para_tokens = self._token_count(paragraph)

            if current_tokens + para_tokens > self.chunk_size:
                if current_text:
                    chunk_text = " ".join(current_text)
                    chunk_id = f"chunk_{document_id}_{chunk_index}"
                    chunks.append(
                        Chunk(
                            text=chunk_text,
                            chunk_id=chunk_id,
                            section_path=section_path,
                            entities_mentioned=[],
                        )
                    )
                    chunk_index += 1

                overlap_paragraphs: List[str] = []
                overlap_token_count = 0
                for prev_para in reversed(current_text):
                    prev_tokens = self._token_count(prev_para)
                    if overlap_token_count + prev_tokens > self.chunk_overlap:
                        break
                    overlap_paragraphs.insert(0, prev_para)
                    overlap_token_count += prev_tokens

                current_text = overlap_paragraphs
                current_tokens = self._token_count(" ".join(overlap_paragraphs))

            current_text.append(paragraph)
            current_tokens += para_tokens

        if current_text:
            chunk_text = " ".join(current_text)
            chunk_id = f"chunk_{document_id}_{chunk_index}"
            chunks.append(
                Chunk(
                    text=chunk_text,
                    chunk_id=chunk_id,
                    section_path=section_path,
                    entities_mentioned=[],
                )
            )

        return chunks


def chunk_text_hierarchical(text: str, document_id: str) -> List[Chunk]:
    chunker = EntityAwareChunker()
    return chunker.chunk_text_hierarchical(text, document_id)
