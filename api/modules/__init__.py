"""
============================================================================
FILE: __init__.py
LOCATION: api/modules/__init__.py
============================================================================

PURPOSE:
    Package initialization for M2KG modules API, providing clean imports
    for the modules package.

ROLE IN PROJECT:
    Provides centralized access to all module-related components including
    models, services, and router.
    - Key responsibility 1: Re-exports module models and services
    - Key responsibility 2: Simplifies imports across the codebase

KEY COMPONENTS:
    - ModuleCreate, ModuleUpdate, ModuleResponse: Pydantic models
    - ModuleListResponse, ModuleStatus: Supporting models
    - ModuleService: Business logic service
    - ModulePublisher: Publishing workflow service
    - modules_router: FastAPI router

DEPENDENCIES:
    - External: None
    - Internal: .models, .service, .publishing, .router

USAGE:
    from api.modules import ModuleService, ModulePublisher, modules_router
============================================================================
"""

from .models import (
    ModuleCreate,
    ModuleUpdate,
    ModuleResponse,
    ModuleListResponse,
    ModuleStatus,
)
from .service import ModuleService
from .publishing import ModulePublisher
from .router import router as modules_router

__all__ = [
    # Models
    "ModuleCreate",
    "ModuleUpdate",
    "ModuleResponse",
    "ModuleListResponse",
    "ModuleStatus",
    # Services
    "ModuleService",
    "ModulePublisher",
    # Router
    "modules_router",
]
