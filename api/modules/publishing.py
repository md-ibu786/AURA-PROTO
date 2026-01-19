# publishing.py
# Module publishing workflow for M2KG system

# Manages module lifecycle transitions (draft → published → archived).
# Maintains published_modules collection for AURA-CHAT access.
# Logs all actions to audit trail for compliance.

# @see: service.py - Base ModuleService for CRUD operations
# @see: router.py - Endpoints that use this publisher
# @note: Uses sync Firestore but methods follow async pattern for future

from typing import Dict, Any, Optional, List
from datetime import datetime

try:
    from .service import ModuleService
    from .models import ModuleStatus, ModuleUpdate
except ImportError:
    from service import ModuleService
    from models import ModuleStatus, ModuleUpdate

try:
    from config import db
except ImportError:
    try:
        from ..config import db
    except ImportError:
        from api.config import db


class ModulePublisher:
    """
    Service for module publishing workflow.
    
    Handles:
    - Publishing modules (draft → published)
    - Unpublishing modules (published → draft)
    - Syncing to published_modules collection for AURA-CHAT
    - Audit trail logging
    """

    PUBLISHED_MODULES_COLLECTION = "published_modules"
    AUDIT_LOG_COLLECTION = "module_audit_log"

    def __init__(self, firestore_db=None):
        """Initialize with optional Firestore client injection."""
        self.db = firestore_db or db
        self.module_service = ModuleService(self.db)
        self.published_collection = self.db.collection(self.PUBLISHED_MODULES_COLLECTION)
        self.audit_collection = self.db.collection(self.AUDIT_LOG_COLLECTION)

    def publish(self, module_id: str, staff_id: str) -> Dict[str, Any]:
        """
        Publish a module for student access.

        Workflow:
        1. Validate module exists and is in DRAFT status
        2. Check module has at least 1 document
        3. Update status to PUBLISHED
        4. Add to published_modules collection (for AURA-CHAT)
        5. Log audit trail

        Args:
            module_id: Module to publish
            staff_id: Staff member publishing the module

        Returns:
            Published module data

        Raises:
            ValueError: If module not found, wrong status, or no documents
        """
        # Get module
        module = self.module_service.get_by_id(module_id)
        if not module:
            raise ValueError(f"Module {module_id} not found")

        current_status = module.get("status")
        
        # Validate status - allow DRAFT or already PUBLISHED (idempotent)
        if current_status not in [ModuleStatus.DRAFT.value, "draft"]:
            if current_status in [ModuleStatus.PUBLISHED.value, "published"]:
                # Already published - return current state
                return {
                    **module,
                    "message": "Module is already published"
                }
            raise ValueError(f"Module must be in DRAFT status to publish (current: {current_status})")

        # Check document count (optional - can publish empty modules)
        doc_count = module.get("document_count", 0)
        if doc_count < 1:
            # Warning but allow publishing
            pass

        now = datetime.utcnow()

        # Update module status
        update_data = ModuleUpdate(status=ModuleStatus.PUBLISHED)
        self.module_service.update(module_id, update_data)

        # Add to published modules (for AURA-CHAT discovery)
        published_doc = {
            "module_id": module_id,
            "name": module["name"],
            "code": module["code"],
            "description": module.get("description"),
            "year": module["year"],
            "semester": module["semester"],
            "document_count": doc_count,
            "published_at": now,
            "published_by": staff_id,
            "student_access": True
        }
        self.published_collection.document(module_id).set(published_doc)

        # Audit log
        self._log_audit(
            module_id=module_id,
            action="PUBLISH",
            staff_id=staff_id,
            details={
                "document_count": doc_count,
                "previous_status": current_status,
                "new_status": ModuleStatus.PUBLISHED.value
            }
        )

        return {
            **module,
            "status": ModuleStatus.PUBLISHED.value,
            "published_at": now.isoformat()
        }

    def unpublish(self, module_id: str, staff_id: str, reason: Optional[str] = None) -> Dict[str, Any]:
        """
        Unpublish a module (hide from students).

        Args:
            module_id: Module to unpublish
            staff_id: Staff member unpublishing
            reason: Optional reason for unpublishing

        Returns:
            Updated module data

        Raises:
            ValueError: If module not found or not published
        """
        module = self.module_service.get_by_id(module_id)
        if not module:
            raise ValueError(f"Module {module_id} not found")

        current_status = module.get("status")
        
        if current_status not in [ModuleStatus.PUBLISHED.value, "published"]:
            raise ValueError(f"Module must be PUBLISHED to unpublish (current: {current_status})")

        now = datetime.utcnow()

        # Update status back to draft
        update_data = ModuleUpdate(status=ModuleStatus.DRAFT)
        self.module_service.update(module_id, update_data)

        # Remove from published modules (AURA-CHAT won't see it)
        self.published_collection.document(module_id).delete()

        # Audit log
        self._log_audit(
            module_id=module_id,
            action="UNPUBLISH",
            staff_id=staff_id,
            details={
                "reason": reason,
                "previous_status": ModuleStatus.PUBLISHED.value,
                "new_status": ModuleStatus.DRAFT.value
            }
        )

        return {
            **module,
            "status": ModuleStatus.DRAFT.value,
            "unpublished_at": now.isoformat()
        }

    def get_published_modules(self) -> List[Dict[str, Any]]:
        """
        Get all published modules for AURA-CHAT.
        
        Returns:
            List of published module documents
        """
        docs = self.published_collection.where("student_access", "==", True).get()
        return [d.to_dict() for d in docs]

    def get_audit_log(self, module_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get audit log for a module.
        
        Args:
            module_id: Module to get audit log for
            limit: Max number of entries to return
            
        Returns:
            List of audit log entries, newest first
        """
        from google.cloud import firestore as fs
        docs = (
            self.audit_collection
            .where("module_id", "==", module_id)
            .order_by("timestamp", direction=fs.Query.DESCENDING)
            .limit(limit)
            .get()
        )
        
        results = []
        for d in docs:
            entry = d.to_dict()
            # Convert Firestore Timestamp to ISO string
            if hasattr(entry.get("timestamp"), "isoformat"):
                entry["timestamp"] = entry["timestamp"].isoformat()
            results.append(entry)
        return results

    def _log_audit(self, module_id: str, action: str, staff_id: str, details: Dict[str, Any]) -> None:
        """
        Log an audit entry.
        
        Args:
            module_id: Module being acted upon
            action: Action type (PUBLISH, UNPUBLISH, etc.)
            staff_id: Staff member performing action
            details: Additional details about the action
        """
        self.audit_collection.add({
            "module_id": module_id,
            "action": action,
            "performed_by": staff_id,
            "timestamp": datetime.utcnow(),
            "details": details
        })
