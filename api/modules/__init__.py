# __init__.py
# Package exports for M2KG modules API

# Provides clean imports for the modules package.
# Usage: from api.modules import ModuleService, ModulePublisher, modules_router

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

