# templates.py
# API router for template management in AURA-NOTES-MANAGER

# Provides endpoints for listing, retrieving, creating, and using
# extraction templates. Supports auto-detection and preview functionality.

# @see: services/extraction_templates.py - Template models and logic
# @see: api/kg_processor.py - Integration with KG processing
# @note: Templates improve extraction quality for structured documents

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from pydantic import BaseModel, Field

# Import template models and services
try:
    from services.extraction_templates import (
        ExtractionTemplate,
        ExtractionOptions,
        TemplateDetectionResult,
        TemplateExtractionResult,
        TemplateExtractor,
        TemplateRegistry,
        get_template_registry,
        get_template_extractor,
    )
except ImportError:
    # Fallback for relative imports
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
    from services.extraction_templates import (
        ExtractionTemplate,
        ExtractionOptions,
        TemplateDetectionResult,
        TemplateExtractionResult,
        TemplateExtractor,
        TemplateRegistry,
        get_template_registry,
        get_template_extractor,
    )

import logging

logger = logging.getLogger(__name__)

# ============================================================================
# ROUTER
# ============================================================================

router = APIRouter(prefix="/v1/templates", tags=["Templates"])


# ============================================================================
# RESPONSE MODELS
# ============================================================================


class TemplatePreviewResult(BaseModel):
    """Preview of extraction without saving."""

    template_id: str
    sections_detected: List[str]
    entities_extracted: int
    relationships_extracted: int
    quality_score: float
    sample_entities: List[Dict[str, Any]]


class TemplateListResponse(BaseModel):
    """Response for listing templates."""

    templates: List[ExtractionTemplate]
    total: int


class DetectTemplateRequest(BaseModel):
    """Request for template detection."""

    content: str = Field(..., min_length=50, description="Document content to analyze")


class PreviewExtractionRequest(BaseModel):
    """Request for extraction preview."""

    content: str = Field(..., min_length=50, description="Document content")
    template_id: str = Field(..., description="Template ID to use")
    max_entities_per_section: int = Field(default=10)
    min_entity_confidence: float = Field(default=0.5)


class CreateTemplateRequest(BaseModel):
    """Request for creating a custom template."""

    name: str = Field(..., min_length=3, max_length=100)
    description: str = Field(..., max_length=500)
    document_patterns: List[str] = Field(default_factory=list)
    sections: List[Dict[str, Any]] = Field(default_factory=list)
    entity_types: List[str] = Field(
        default_factory=lambda: ["Topic", "Concept", "Methodology", "Finding"]
    )
    relationship_types: List[str] = Field(
        default_factory=lambda: ["DEFINES", "DEPENDS_ON", "USES", "RELATED_TO"]
    )


# ============================================================================
# DEPENDENCY INJECTION
# ============================================================================


def get_registry() -> TemplateRegistry:
    """Get template registry dependency."""
    return get_template_registry()


def get_extractor() -> TemplateExtractor:
    """Get template extractor dependency."""
    return get_template_extractor()


# ============================================================================
# ENDPOINTS
# ============================================================================


@router.get("/", response_model=TemplateListResponse)
async def list_templates(
    include_custom: bool = Query(True, description="Include custom templates"),
    registry: TemplateRegistry = Depends(get_registry),
) -> TemplateListResponse:
    """
    List all available extraction templates.

    Returns built-in templates and optionally custom templates.
    """
    try:
        templates = registry.list_all(include_custom=include_custom)
        return TemplateListResponse(templates=templates, total=len(templates))
    except Exception as e:
        logger.error(f"Error listing templates: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{template_id}", response_model=ExtractionTemplate)
async def get_template(
    template_id: str,
    registry: TemplateRegistry = Depends(get_registry),
) -> ExtractionTemplate:
    """
    Get a specific template by ID.

    Args:
        template_id: Template identifier (e.g., 'lecture_notes', 'research_paper')
    """
    template = registry.get(template_id)
    if not template:
        raise HTTPException(
            status_code=404, detail=f"Template not found: {template_id}"
        )
    return template


@router.post("/", response_model=ExtractionTemplate)
async def create_template(
    request: CreateTemplateRequest,
    registry: TemplateRegistry = Depends(get_registry),
) -> ExtractionTemplate:
    """
    Create a custom extraction template.

    Custom templates can define specialized extraction patterns for
    domain-specific documents.
    """
    try:
        # Import SectionTemplate and TemplateType for building template
        from services.extraction_templates import SectionTemplate, TemplateType

        # Generate unique ID from name
        import hashlib
        template_id = f"custom_{hashlib.md5(request.name.lower().encode()).hexdigest()[:8]}"

        # Convert section dicts to SectionTemplate objects
        sections = []
        for i, section_dict in enumerate(request.sections):
            sections.append(
                SectionTemplate(
                    name=section_dict.get("name", f"Section {i+1}"),
                    optional=section_dict.get("optional", False),
                    patterns=section_dict.get("patterns", []),
                    entity_focus=section_dict.get("entity_focus", ["Concept"]),
                    order=i,
                )
            )

        template = ExtractionTemplate(
            id=template_id,
            name=request.name,
            description=request.description,
            template_type=TemplateType.GENERIC,
            document_patterns=request.document_patterns,
            sections=sections,
            entity_types=request.entity_types,
            relationship_types=request.relationship_types,
            is_builtin=False,
            created_by="user",  # Would be actual user ID in auth context
        )

        registry.register(template)
        logger.info(f"Created custom template: {template_id}")

        return template

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating template: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/detect", response_model=TemplateDetectionResult)
async def detect_template(
    request: DetectTemplateRequest,
    registry: TemplateRegistry = Depends(get_registry),
) -> TemplateDetectionResult:
    """
    Detect the best matching template for content.

    Analyzes document structure and patterns to determine the most
    appropriate template for extraction.
    """
    try:
        template, confidence = registry.detect_template(request.content)
        alternatives = registry.get_detection_alternatives(request.content, top_k=3)

        return TemplateDetectionResult(
            detected_template_id=template.id,
            detected_template_name=template.name,
            confidence=round(confidence, 3),
            alternatives=alternatives,
        )

    except Exception as e:
        logger.error(f"Error detecting template: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/preview", response_model=TemplatePreviewResult)
async def preview_extraction(
    request: PreviewExtractionRequest,
    extractor: TemplateExtractor = Depends(get_extractor),
) -> TemplatePreviewResult:
    """
    Preview extraction results without saving.

    Allows users to see what entities would be extracted with a
    given template before committing to full processing.
    """
    try:
        options = ExtractionOptions(
            max_entities_per_section=request.max_entities_per_section,
            min_entity_confidence=request.min_entity_confidence,
        )

        result = extractor.extract_with_template(
            content=request.content,
            template_id=request.template_id,
            options=options,
        )

        # Get sample entities (first 5)
        sample_entities = result.entities[:5]

        return TemplatePreviewResult(
            template_id=result.template_id,
            sections_detected=result.sections_detected,
            entities_extracted=len(result.entities),
            relationships_extracted=len(result.relationships),
            quality_score=round(result.quality_score, 3),
            sample_entities=sample_entities,
        )

    except Exception as e:
        logger.error(f"Error previewing extraction: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{template_id}")
async def delete_template(
    template_id: str,
    registry: TemplateRegistry = Depends(get_registry),
) -> Dict[str, str]:
    """
    Delete a custom template.

    Only custom templates can be deleted. Built-in templates cannot be removed.
    """
    template = registry.get(template_id)
    if not template:
        raise HTTPException(
            status_code=404, detail=f"Template not found: {template_id}"
        )

    if template.is_builtin:
        raise HTTPException(
            status_code=400, detail="Cannot delete built-in templates"
        )

    # Remove from registry (would need to add this method)
    try:
        del registry._templates[template_id]
        logger.info(f"Deleted custom template: {template_id}")
        return {"status": "deleted", "template_id": template_id}
    except Exception as e:
        logger.error(f"Error deleting template: {e}")
        raise HTTPException(status_code=500, detail=str(e))
