# kg/__init__.py
# Package init for KG processing API router

# Exports the kg_router for inclusion in main.py.
# Provides per-document KG status tracking and batch processing endpoints.

# @see: router.py - FastAPI router with KG endpoints
# @see: main.py - Includes this router with /api/v1 prefix

from .router import router as kg_router

__all__ = ["kg_router"]
