# service.py
# Business logic for M2KG Module CRUD operations with Firestore

# Provides ModuleService class that handles all module data operations.
# Modules are stored in Firestore 'modules' collection with ID format:
# {code}_{year}_S{semester} (e.g., CS201_2026_S1)

# @see: models.py - Pydantic schemas used by this service
# @see: router.py - FastAPI endpoints that call this service
# @note: Uses sync Firestore client, but methods are async for future flexibility

from typing import List, Optional, Dict, Any
from datetime import datetime
from google.cloud import firestore

try:
    from .models import ModuleCreate, ModuleUpdate, ModuleStatus
except ImportError:
    from models import ModuleCreate, ModuleUpdate, ModuleStatus

try:
    from config import db
except ImportError:
    try:
        from ..config import db
    except ImportError:
        from api.config import db


class ModuleService:
    """Service for M2KG Module CRUD operations with Firestore."""

    COLLECTION = "m2kg_modules"  # Prefixed to avoid collision with hierarchy modules

    def __init__(self, firestore_db=None):
        """Initialize with optional Firestore client injection for testing."""
        self.db = firestore_db or db
        self.collection = self.db.collection(self.COLLECTION)

    def create(self, user_id: str, module_data: ModuleCreate) -> Dict[str, Any]:
        """
        Create a new module.
        
        Args:
            user_id: ID of staff user creating the module
            module_data: Module creation data
            
        Returns:
            Created module document as dict
            
        Raises:
            ValueError: If module with same ID already exists
        """
        # Generate deterministic module ID
        module_id = f"{module_data.code.upper()}_{module_data.year}_S{module_data.semester}"
        
        doc_ref = self.collection.document(module_id)
        
        # Check if already exists
        if doc_ref.get().exists:
            raise ValueError(f"Module with ID '{module_id}' already exists")
        
        now = datetime.utcnow()
        module_doc = {
            "id": module_id,
            "name": module_data.name,
            "code": module_data.code.upper(),
            "description": module_data.description,
            "year": module_data.year,
            "semester": module_data.semester,
            "status": ModuleStatus.DRAFT.value,
            "document_count": 0,
            "created_by": user_id,
            "created_at": now,
            "updated_at": now
        }
        
        doc_ref.set(module_doc)
        return module_doc

    def get_by_id(self, module_id: str) -> Optional[Dict[str, Any]]:
        """
        Get module by ID.
        
        Args:
            module_id: Module ID (e.g., CS201_2026_S1)
            
        Returns:
            Module document as dict, or None if not found
        """
        doc = self.collection.document(module_id).get()
        if not doc.exists:
            return None
        
        data = doc.to_dict()
        # Convert Firestore Timestamps to datetime
        if hasattr(data.get('created_at'), 'timestamp'):
            data['created_at'] = data['created_at'].timestamp()
        if hasattr(data.get('updated_at'), 'timestamp'):
            data['updated_at'] = data['updated_at'].timestamp()
        return data

    def list(
        self,
        user_id: Optional[str] = None,
        status: Optional[ModuleStatus] = None,
        year: Optional[int] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """
        List modules with filters and pagination.
        
        Args:
            user_id: Filter by creator (optional)
            status: Filter by status (optional)
            year: Filter by year (optional)
            page: Page number (1-indexed)
            page_size: Items per page
            
        Returns:
            Dict with modules list, total, page, page_size
        """
        query = self.collection

        # Apply filters
        if user_id:
            query = query.where("created_by", "==", user_id)
        if status:
            query = query.where("status", "==", status.value)
        if year:
            query = query.where("year", "==", year)

        # Order by created_at descending
        query = query.order_by("created_at", direction=firestore.Query.DESCENDING)

        # Get total count (note: Firestore doesn't have efficient count)
        all_docs = list(query.stream())
        total = len(all_docs)

        # Apply pagination
        offset = (page - 1) * page_size
        paginated_docs = all_docs[offset:offset + page_size]

        modules = []
        for doc in paginated_docs:
            data = doc.to_dict()
            # Ensure datetime serialization
            if hasattr(data.get('created_at'), 'isoformat'):
                pass  # Already datetime
            modules.append(data)

        return {
            "modules": modules,
            "total": total,
            "page": page,
            "page_size": page_size
        }

    def update(self, module_id: str, update_data: ModuleUpdate) -> Optional[Dict[str, Any]]:
        """
        Update module fields.
        
        Args:
            module_id: Module ID to update
            update_data: Fields to update
            
        Returns:
            Updated module dict, or None if not found
        """
        doc_ref = self.collection.document(module_id)
        doc = doc_ref.get()

        if not doc.exists:
            return None

        # Build update dict from non-None fields
        update_fields = {}
        if update_data.name is not None:
            update_fields["name"] = update_data.name
        if update_data.description is not None:
            update_fields["description"] = update_data.description
        if update_data.status is not None:
            update_fields["status"] = update_data.status.value
        
        if not update_fields:
            # Nothing to update, return current state
            return doc.to_dict()
            
        update_fields["updated_at"] = datetime.utcnow()

        doc_ref.update(update_fields)
        return doc_ref.get().to_dict()

    def delete(self, module_id: str) -> bool:
        """
        Soft delete module by archiving.
        
        Args:
            module_id: Module ID to delete
            
        Returns:
            True if deleted, False if not found
        """
        doc_ref = self.collection.document(module_id)
        doc = doc_ref.get()

        if not doc.exists:
            return False

        doc_ref.update({
            "status": ModuleStatus.ARCHIVED.value,
            "updated_at": datetime.utcnow()
        })
        return True

    def increment_document_count(self, module_id: str, delta: int = 1) -> bool:
        """
        Increment or decrement document count for module.
        
        Called when documents are assigned/removed from module.
        
        Args:
            module_id: Module ID
            delta: Amount to change (positive or negative)
            
        Returns:
            True if updated, False if module not found
        """
        doc_ref = self.collection.document(module_id)
        doc = doc_ref.get()

        if not doc.exists:
            return False

        current_count = doc.to_dict().get("document_count", 0)
        new_count = max(0, current_count + delta)  # Prevent negative counts
        
        doc_ref.update({
            "document_count": new_count,
            "updated_at": datetime.utcnow()
        })
        return True

    def publish(self, module_id: str) -> Optional[Dict[str, Any]]:
        """
        Publish a module (change status from draft to published).
        
        Args:
            module_id: Module ID to publish
            
        Returns:
            Updated module dict, or None if not found
        """
        doc_ref = self.collection.document(module_id)
        doc = doc_ref.get()

        if not doc.exists:
            return None

        now = datetime.utcnow()
        doc_ref.update({
            "status": ModuleStatus.PUBLISHED.value,
            "published_at": now,
            "updated_at": now
        })
        return doc_ref.get().to_dict()
