# __init__.py
# Routers package for AURA-NOTES-MANAGER API

# Re-exports router instances for convenient import in main.py.
# Each router handles a specific domain of the API.

# @see: api/routers/query.py - Knowledge graph query endpoints
# @see: api/main.py - Router registration

from api.routers.query import router as query_router

__all__ = ["query_router"]
