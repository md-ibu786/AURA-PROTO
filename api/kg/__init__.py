"""
============================================================================
FILE: __init__.py
LOCATION: api/kg/__init__.py
============================================================================

PURPOSE:
    Package initializer for the KG processing API router module.

ROLE IN PROJECT:
    Exports the kg_router for inclusion in main.py. Provides per-document
    KG status tracking, batch processing, queue monitoring, and batch
    deletion endpoints for the knowledge graph pipeline.

KEY COMPONENTS:
    - kg_router: FastAPI router with /kg prefix and all KG endpoints

DEPENDENCIES:
    - External: None
    - Internal: api/kg/router.py

USAGE:
    from api.kg import kg_router
    app.include_router(kg_router, prefix="/api/v1")
============================================================================
"""
from .router import router as kg_router

__all__ = ["kg_router"]
