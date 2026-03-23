"""
========================================================================
FILE: __init__.py
LOCATION: AURA-NOTES-MANAGER/services/__init__.py
========================================================================

PURPOSE:
    Services package initialization for AURA-NOTES-MANAGER AI/ML layer.

ROLE IN PROJECT:
    Makes services directory a proper Python package so that
    unittest.mock.patch can resolve dotted paths like
    services.llm_entity_extractor for test patching.

KEY COMPONENTS:
    - llm_entity_extractor: LLM-powered entity extraction
    - embeddings: Text embedding service
    - summarizer: University notes summarization
    - vertex_ai_client: Vertex AI integration

DEPENDENCIES:
    - External: None (package marker only)
    - Internal: None

USAGE:
    Automatically imported by Python package resolution.
========================================================================
"""
