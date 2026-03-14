"""
============================================================================
FILE: __init__.py
LOCATION: api/routers/__init__.py
============================================================================

PURPOSE:
    Package initialization for AURA-NOTES-MANAGER API routers, re-exporting
    router instances for convenient import in main.py.

ROLE IN PROJECT:
    Provides clean centralized access to all API routers. Each router handles
    a specific domain of the API.
    - Key responsibility 1: Re-exports router instances
    - Key responsibility 2: Simplifies imports in main.py

KEY COMPONENTS:
    - summaries_router: Auto-summarization endpoints
    - templates_router: Extraction template endpoints
    - schema_router: Schema validation and migration endpoints
    - graph_preview_router: Graph preview endpoints

DEPENDENCIES:
    - External: None
    - Internal: api.routers.summaries, templates, schema, graph_preview

USAGE:
    from api.routers import summaries_router, templates_router
============================================================================
"""

from api.routers.summaries import router as summaries_router
from api.routers.templates import router as templates_router
from api.routers.schema import router as schema_router
from api.routers.graph_preview import router as graph_preview_router

__all__ = [
    "summaries_router",
    "templates_router",
    "schema_router",
    "graph_preview_router",
]
