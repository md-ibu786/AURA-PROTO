---
phase: 10
slug: chunk-labeling-for-document-to-kg-pipeline
status: draft
created: 2026-04-23
---

# Phase 10 — UI Design Contract

> Visual and interaction specifications for chunk labeling in the Knowledge Graph pipeline.

---

## Overview

Phase 10 introduces **semantic chunk labels** to the Document-to-KG Pipeline. The UI must:
1. Display chunk labels in the Graph Visualizer and node detail panels
2. Provide label filtering in the explorer/KG views
3. Show labeling progress during document processing

---

## Screens / Views Affected

### 1. Graph Visualizer (Node Labels)

**Current:** Chunk nodes show text preview + position.
**New:** Chunk nodes show **color-coded label chips** alongside text preview.

```
┌─────────────────────────────────────┐
│  [definition] The quick brown...    │
│  Position: 12 | Tokens: 256         │
└─────────────────────────────────────┘
```

**Label chip specs:**
- Height: 20px
- Padding: 4px 8px
- Border-radius: 4px
- Font: 11px monospace
- Background: per-label color (see palette)
- Text: white or dark based on contrast

### 2. Node Detail Panel (Chunk Inspector)

**New section:** `Labels`
- List all assigned labels as chips
- Show confidence score per label (if available)
- Allow copy-to-clipboard

### 3. Processing Queue / Status

**New stage:** `Labeling`
- Progress bar step between `Chunking` and `Entity Extraction`
- Estimated time: ~1s per 5 chunks

### 4. Filter Bar (Explorer / KG)

**New filter:** `Chunk Labels`
- Multi-select dropdown
- Options populated from controlled vocabulary
- Filter applies to visible chunk nodes

---

## Color Palette (Label Chips)

| Label | Background | Text |
|-------|-----------|------|
| definition | `#2563EB` (blue-600) | white |
| theorem | `#7C3AED` (violet-600) | white |
| example | `#059669` (emerald-600) | white |
| methodology | `#DC2626` (red-600) | white |
| finding | `#D97706` (amber-600) | white |
| introduction | `#4B5563` (gray-600) | white |
| conclusion | `#4B5563` (gray-600) | white |
| related_work | `#0891B2` (cyan-600) | white |
| discussion | `#9333EA` (purple-600) | white |
| appendix | `#6B7280` (gray-500) | white |
| figure_table | `#EA580C` (orange-600) | white |

*Fallback for unknown labels: `#374151` (gray-700)*

---

## Interaction Patterns

**Hover on label chip:**
- Tooltip: "Confidence: 0.92" (if available)
- Delay: 300ms

**Click label chip in filter bar:**
- Toggle active state
- Graph re-renders with filtered nodes
- URL param updates: `?labels=definition,theorem`

**Click label chip in node detail:**
- No action (read-only display)

---

## Accessibility

- Chips must meet WCAG 4.5:1 contrast ratio
- Label text must be readable by screen readers
- Filter dropdown must be keyboard-navigable

---

## Responsive Behavior

- Desktop: chips inline with node text
- Tablet: chips wrap below node text
- Mobile: single chip row, truncate with "+N" overflow

---

## Components Required

| Component | Location | Props |
|-----------|----------|-------|
| `ChunkLabelBadge` | `frontend/src/features/kg/components/` | `labels: string[]`, `confidence?: Record<string, number>` |
| `ChunkLabelFilter` | `frontend/src/features/kg/components/` | `options: string[]`, `selected: string[]`, `onChange` |
| `LabelColorMap` | `frontend/src/features/kg/lib/` | `getColor(label): {bg, text}` |

---

## State / Data Flow

1. Backend: `chunk_labels` array stored on Neo4j `Chunk` node
2. API: `GET /api/kg/nodes/{id}` includes `chunk_labels`
3. Frontend: TanStack Query caches node data
4. UI: Components read from cache, filter bar controls local + URL state

---

## Out of Scope (Deferred)

- User-editable labels post-processing (v1.3+)
- Label suggestion UI during upload (v1.3+)
- Bulk label operations (v1.3+)

---

*Phase: 10-chunk-labeling-for-document-to-kg-pipeline*
*UI contract created: 2026-04-23*
