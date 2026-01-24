# __init__.py
# Routers package for AURA-NOTES-MANAGER API

# Re-exports router instances for convenient import in main.py.
# Each router handles a specific domain of the API.

# @see: api/routers/query.py - Knowledge graph query endpoints
# @see: api/routers/summaries.py - Auto-summarization endpoints
# @see: api/routers/templates.py - Extraction template endpoints
# @see: api/routers/schema.py - Schema validation and migration endpoints
# @see: api/main.py - Router registration

from api.routers.query import router as query_router
from api.routers.summaries import router as summaries_router
from api.routers.templates import router as templates_router
from api.routers.schema import router as schema_router

__all__ = ["query_router", "summaries_router", "templates_router", "schema_router"]
