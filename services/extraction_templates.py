# extraction_templates.py
# Template-based extraction service for structured document processing

# Defines specialized extraction patterns for different note types (lecture notes,
# research papers, meeting notes, lab reports, case studies). Each template specifies
# expected sections, entity types, and relationships to improve KG extraction quality.

# @see: api/kg_processor.py - Integration point for template-based extraction
# @see: services/llm_entity_extractor.py - Entity extraction service
# @note: Templates can be auto-detected based on document structure patterns

from __future__ import annotations

import hashlib
import logging
import re
from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Tuple

from pydantic import BaseModel, Field

# ============================================================================
# LOGGING
# ============================================================================

logger = logging.getLogger(__name__)


# ============================================================================
# ENUMS
# ============================================================================


class TemplateType(str, Enum):
    """Supported template types for document extraction."""

    LECTURE_NOTES = "lecture_notes"
    RESEARCH_PAPER = "research_paper"
    MEETING_NOTES = "meeting_notes"
    LAB_REPORT = "lab_report"
    CASE_STUDY = "case_study"
    GENERIC = "generic"


# ============================================================================
# PYDANTIC MODELS
# ============================================================================


class SectionTemplate(BaseModel):
    """Template for a document section within an extraction template."""

    name: str = Field(..., description="Section name (e.g., 'Introduction')")
    optional: bool = Field(
        default=False, description="Whether this section is optional"
    )
    patterns: List[str] = Field(
        default_factory=list,
        description="Regex patterns to identify this section in text",
    )
    entity_focus: List[str] = Field(
        default_factory=list,
        description="Primary entity types to extract from this section",
    )
    order: int = Field(
        default=0, description="Expected order of this section in document"
    )


class ExtractionTemplate(BaseModel):
    """
    Template for structured extraction based on document type.

    Templates define expected document structure, section patterns,
    and extraction focus areas for improved KG quality.
    """

    id: str = Field(..., description="Unique template identifier")
    name: str = Field(..., description="Human-readable template name")
    description: str = Field(..., description="Template purpose and usage")
    template_type: TemplateType = Field(
        ..., description="Category of template"
    )
    document_patterns: List[str] = Field(
        default_factory=list,
        description="Regex patterns to detect this document type",
    )
    sections: List[SectionTemplate] = Field(
        default_factory=list, description="Expected sections in this document type"
    )
    entity_types: List[str] = Field(
        default_factory=lambda: ["Topic", "Concept", "Methodology", "Finding"],
        description="Entity types to extract",
    )
    relationship_types: List[str] = Field(
        default_factory=lambda: ["DEFINES", "DEPENDS_ON", "USES", "RELATED_TO"],
        description="Relationship types to extract",
    )
    extraction_prompts: Dict[str, str] = Field(
        default_factory=dict,
        description="Section-specific extraction prompts",
    )
    is_builtin: bool = Field(
        default=True, description="Whether this is a built-in template"
    )
    created_by: Optional[str] = Field(
        default=None, description="User ID who created custom template"
    )


class DetectedSection(BaseModel):
    """A section detected in document content."""

    section_template: SectionTemplate
    start_pos: int = Field(..., description="Start position in text")
    end_pos: int = Field(..., description="End position in text")
    content: str = Field(..., description="Section content")
    confidence: float = Field(
        default=0.8, ge=0.0, le=1.0, description="Detection confidence"
    )


class SectionExtractionResult(BaseModel):
    """Result of extracting from a single section."""

    section_name: str
    entities: List[Dict[str, Any]] = Field(default_factory=list)
    relationships: List[Dict[str, Any]] = Field(default_factory=list)


class TemplateExtractionResult(BaseModel):
    """Complete result of template-based extraction."""

    template_id: str
    template_name: str
    sections_detected: List[str] = Field(default_factory=list)
    sections_missing: List[str] = Field(default_factory=list)
    section_results: List[SectionExtractionResult] = Field(default_factory=list)
    entities: List[Dict[str, Any]] = Field(default_factory=list)
    relationships: List[Dict[str, Any]] = Field(default_factory=list)
    quality_score: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Template fit quality score"
    )


class TemplateDetectionResult(BaseModel):
    """Result of template detection."""

    detected_template_id: str
    detected_template_name: str
    confidence: float = Field(ge=0.0, le=1.0)
    alternatives: List[Dict[str, Any]] = Field(default_factory=list)


class TemplatePreviewResult(BaseModel):
    """Preview of extraction without saving."""

    template_id: str
    sections_detected: List[str]
    entities_extracted: int
    relationships_extracted: int
    quality_score: float
    sample_entities: List[Dict[str, Any]]


class ExtractionOptions(BaseModel):
    """Options for template-based extraction."""

    max_entities_per_section: int = Field(default=20)
    min_entity_confidence: float = Field(default=0.5)
    include_relationships: bool = Field(default=True)
    max_relationships: int = Field(default=50)


# ============================================================================
# BUILT-IN TEMPLATES
# ============================================================================


def _create_lecture_notes_template() -> ExtractionTemplate:
    """Create template for lecture notes."""
    return ExtractionTemplate(
        id="lecture_notes",
        name="Lecture Notes",
        description="Template for academic lecture notes with topics, concepts, and examples",
        template_type=TemplateType.LECTURE_NOTES,
        document_patterns=[
            r"(?i)lecture\s*\d*",
            r"(?i)class\s*notes?",
            r"(?i)professor|instructor",
            r"(?i)today.*(learn|cover|discuss)",
            r"(?i)outline|agenda|objectives",
            r"(?i)example\s*\d*[:.\s]",
            r"(?i)chapter\s*\d+",
        ],
        sections=[
            SectionTemplate(
                name="Introduction",
                optional=False,
                patterns=[
                    r"(?i)^#+\s*introduction",
                    r"(?i)^introduction\s*$",
                    r"(?i)^overview",
                    r"(?i)today.*(learn|cover)",
                ],
                entity_focus=["Topic"],
                order=0,
            ),
            SectionTemplate(
                name="Main Topics",
                optional=False,
                patterns=[
                    r"(?i)^#+\s*main\s*topic",
                    r"(?i)^#+\s*core\s*concept",
                    r"(?i)^#+\s*key\s*point",
                ],
                entity_focus=["Topic", "Concept"],
                order=1,
            ),
            SectionTemplate(
                name="Key Concepts",
                optional=True,
                patterns=[
                    r"(?i)^#+\s*key\s*concept",
                    r"(?i)^#+\s*definition",
                    r"(?i)^#+\s*terminology",
                ],
                entity_focus=["Concept"],
                order=2,
            ),
            SectionTemplate(
                name="Examples",
                optional=True,
                patterns=[
                    r"(?i)^#+\s*example",
                    r"(?i)for\s*example",
                    r"(?i)^#+\s*case\s*stud",
                    r"(?i)^#+\s*illustration",
                ],
                entity_focus=["Methodology"],
                order=3,
            ),
            SectionTemplate(
                name="Summary",
                optional=True,
                patterns=[
                    r"(?i)^#+\s*summary",
                    r"(?i)^#+\s*conclusion",
                    r"(?i)^#+\s*recap",
                    r"(?i)^#+\s*key\s*takeaway",
                ],
                entity_focus=["Finding"],
                order=4,
            ),
        ],
        entity_types=["Topic", "Concept", "Methodology", "Finding"],
        relationship_types=["DEFINES", "EXPLAINS", "ILLUSTRATES", "RELATED_TO"],
        extraction_prompts={
            "Introduction": "Focus on identifying main topics and learning objectives.",
            "Main Topics": "Extract core concepts and their definitions.",
            "Key Concepts": "Identify key terminology and technical definitions.",
            "Examples": "Extract practical applications and methodologies.",
            "Summary": "Identify key findings and conclusions.",
        },
    )


def _create_research_paper_template() -> ExtractionTemplate:
    """Create template for research papers."""
    return ExtractionTemplate(
        id="research_paper",
        name="Research Paper",
        description="Template for academic research papers with standard sections",
        template_type=TemplateType.RESEARCH_PAPER,
        document_patterns=[
            r"(?i)^abstract\s*$",
            r"(?i)^#+\s*abstract",
            r"(?i)^#+\s*methodology",
            r"(?i)^#+\s*results",
            r"(?i)^#+\s*discussion",
            r"(?i)^#+\s*references",
            r"(?i)^#+\s*literature\s*review",
            r"(?i)hypothesis|null\s*hypothesis",
            r"(?i)p-value|significance\s*level",
            r"(?i)doi:|arxiv:",
        ],
        sections=[
            SectionTemplate(
                name="Abstract",
                optional=False,
                patterns=[r"(?i)^#+\s*abstract", r"(?i)^abstract\s*$"],
                entity_focus=["Topic", "Finding"],
                order=0,
            ),
            SectionTemplate(
                name="Introduction",
                optional=False,
                patterns=[r"(?i)^#+\s*introduction", r"(?i)^1\.\s*introduction"],
                entity_focus=["Topic", "Concept"],
                order=1,
            ),
            SectionTemplate(
                name="Methodology",
                optional=False,
                patterns=[
                    r"(?i)^#+\s*method",
                    r"(?i)^#+\s*materials?\s*and\s*methods?",
                    r"(?i)^#+\s*experimental\s*design",
                ],
                entity_focus=["Methodology"],
                order=2,
            ),
            SectionTemplate(
                name="Results",
                optional=False,
                patterns=[
                    r"(?i)^#+\s*results?",
                    r"(?i)^#+\s*finding",
                    r"(?i)^#+\s*analysis",
                ],
                entity_focus=["Finding"],
                order=3,
            ),
            SectionTemplate(
                name="Discussion",
                optional=True,
                patterns=[r"(?i)^#+\s*discussion", r"(?i)^#+\s*interpretation"],
                entity_focus=["Concept", "Finding"],
                order=4,
            ),
            SectionTemplate(
                name="Conclusion",
                optional=True,
                patterns=[
                    r"(?i)^#+\s*conclusion",
                    r"(?i)^#+\s*summary\s*and\s*conclusion",
                ],
                entity_focus=["Finding"],
                order=5,
            ),
        ],
        entity_types=["Topic", "Concept", "Methodology", "Finding"],
        relationship_types=[
            "USES",
            "SUPPORTS",
            "CONTRADICTS",
            "EXTENDS",
            "RELATED_TO",
        ],
        extraction_prompts={
            "Abstract": "Extract main findings and key contributions.",
            "Introduction": "Identify research context and main concepts.",
            "Methodology": "Extract research methods and techniques used.",
            "Results": "Identify key findings and statistical results.",
            "Discussion": "Extract interpretations and implications.",
            "Conclusion": "Identify final conclusions and recommendations.",
        },
    )


def _create_meeting_notes_template() -> ExtractionTemplate:
    """Create template for meeting notes."""
    return ExtractionTemplate(
        id="meeting_notes",
        name="Meeting Notes",
        description="Template for meeting notes with attendees, agenda, and action items",
        template_type=TemplateType.MEETING_NOTES,
        document_patterns=[
            r"(?i)meeting\s*notes?",
            r"(?i)attendance|attendees?",
            r"(?i)^#+\s*agenda",
            r"(?i)action\s*item",
            r"(?i)decision:?",
            r"(?i)assigned\s*to",
            r"(?i)due\s*date",
            r"(?i)minutes?\s*of\s*meeting",
            r"(?i)MoM\s*[-:]",
        ],
        sections=[
            SectionTemplate(
                name="Attendees",
                optional=True,
                patterns=[
                    r"(?i)^#+\s*attendees?",
                    r"(?i)^#+\s*participants?",
                    r"(?i)^#+\s*present",
                ],
                entity_focus=["Topic"],
                order=0,
            ),
            SectionTemplate(
                name="Agenda",
                optional=True,
                patterns=[r"(?i)^#+\s*agenda", r"(?i)^#+\s*topics?\s*to\s*discuss"],
                entity_focus=["Topic"],
                order=1,
            ),
            SectionTemplate(
                name="Discussion",
                optional=False,
                patterns=[
                    r"(?i)^#+\s*discussion",
                    r"(?i)^#+\s*notes",
                    r"(?i)^#+\s*minutes?",
                ],
                entity_focus=["Topic", "Concept"],
                order=2,
            ),
            SectionTemplate(
                name="Action Items",
                optional=True,
                patterns=[
                    r"(?i)^#+\s*action\s*item",
                    r"(?i)^#+\s*next\s*step",
                    r"(?i)^#+\s*to-?do",
                ],
                entity_focus=["Methodology"],
                order=3,
            ),
            SectionTemplate(
                name="Decisions",
                optional=True,
                patterns=[
                    r"(?i)^#+\s*decision",
                    r"(?i)^#+\s*conclusion",
                    r"(?i)^#+\s*resolution",
                ],
                entity_focus=["Finding"],
                order=4,
            ),
        ],
        entity_types=["Topic", "Concept", "Methodology", "Finding"],
        relationship_types=["ASSIGNED_TO", "DEPENDS_ON", "FOLLOWS", "RELATED_TO"],
        extraction_prompts={
            "Attendees": "Identify participants and their roles.",
            "Agenda": "Extract topics and planned discussions.",
            "Discussion": "Identify key points and concepts discussed.",
            "Action Items": "Extract actionable tasks and assignments.",
            "Decisions": "Identify conclusions and decisions made.",
        },
    )


def _create_lab_report_template() -> ExtractionTemplate:
    """Create template for lab reports."""
    return ExtractionTemplate(
        id="lab_report",
        name="Lab Report",
        description="Template for laboratory reports with procedure, observations, and analysis",
        template_type=TemplateType.LAB_REPORT,
        document_patterns=[
            r"(?i)lab(oratory)?\s*report",
            r"(?i)^#+\s*objective",
            r"(?i)^#+\s*materials?",
            r"(?i)^#+\s*procedure",
            r"(?i)^#+\s*observations?",
            r"(?i)experiment\s*\d+",
            r"(?i)hypothesis",
            r"(?i)data\s*table",
        ],
        sections=[
            SectionTemplate(
                name="Objective",
                optional=False,
                patterns=[
                    r"(?i)^#+\s*objective",
                    r"(?i)^#+\s*purpose",
                    r"(?i)^#+\s*aim",
                ],
                entity_focus=["Topic"],
                order=0,
            ),
            SectionTemplate(
                name="Materials",
                optional=True,
                patterns=[
                    r"(?i)^#+\s*materials?",
                    r"(?i)^#+\s*equipment",
                    r"(?i)^#+\s*apparatus",
                ],
                entity_focus=["Concept"],
                order=1,
            ),
            SectionTemplate(
                name="Procedure",
                optional=False,
                patterns=[
                    r"(?i)^#+\s*procedure",
                    r"(?i)^#+\s*method",
                    r"(?i)^#+\s*steps?",
                ],
                entity_focus=["Methodology"],
                order=2,
            ),
            SectionTemplate(
                name="Observations",
                optional=True,
                patterns=[
                    r"(?i)^#+\s*observations?",
                    r"(?i)^#+\s*data",
                    r"(?i)^#+\s*results?",
                ],
                entity_focus=["Finding"],
                order=3,
            ),
            SectionTemplate(
                name="Analysis",
                optional=True,
                patterns=[
                    r"(?i)^#+\s*analysis",
                    r"(?i)^#+\s*calculation",
                    r"(?i)^#+\s*interpretation",
                ],
                entity_focus=["Finding", "Concept"],
                order=4,
            ),
            SectionTemplate(
                name="Conclusion",
                optional=True,
                patterns=[r"(?i)^#+\s*conclusion", r"(?i)^#+\s*summary"],
                entity_focus=["Finding"],
                order=5,
            ),
        ],
        entity_types=["Topic", "Concept", "Methodology", "Finding"],
        relationship_types=["USES", "PRODUCES", "VALIDATES", "RELATED_TO"],
        extraction_prompts={
            "Objective": "Extract the main purpose and goals of the experiment.",
            "Materials": "Identify equipment and materials used.",
            "Procedure": "Extract methodologies and steps performed.",
            "Observations": "Identify key data and observations.",
            "Analysis": "Extract interpretations and calculations.",
            "Conclusion": "Identify final conclusions and findings.",
        },
    )


def _create_case_study_template() -> ExtractionTemplate:
    """Create template for case studies."""
    return ExtractionTemplate(
        id="case_study",
        name="Case Study",
        description="Template for case studies with background, problem, and solution analysis",
        template_type=TemplateType.CASE_STUDY,
        document_patterns=[
            r"(?i)case\s*study",
            r"(?i)^#+\s*background",
            r"(?i)^#+\s*problem\s*statement",
            r"(?i)^#+\s*solution",
            r"(?i)^#+\s*lessons?\s*learned",
            r"(?i)client|stakeholder",
            r"(?i)challenge|opportunity",
        ],
        sections=[
            SectionTemplate(
                name="Background",
                optional=False,
                patterns=[
                    r"(?i)^#+\s*background",
                    r"(?i)^#+\s*context",
                    r"(?i)^#+\s*introduction",
                    r"(?i)^#+\s*overview",
                ],
                entity_focus=["Topic", "Concept"],
                order=0,
            ),
            SectionTemplate(
                name="Problem",
                optional=False,
                patterns=[
                    r"(?i)^#+\s*problem",
                    r"(?i)^#+\s*challenge",
                    r"(?i)^#+\s*issue",
                ],
                entity_focus=["Concept"],
                order=1,
            ),
            SectionTemplate(
                name="Analysis",
                optional=True,
                patterns=[
                    r"(?i)^#+\s*analysis",
                    r"(?i)^#+\s*approach",
                    r"(?i)^#+\s*evaluation",
                ],
                entity_focus=["Methodology"],
                order=2,
            ),
            SectionTemplate(
                name="Solution",
                optional=False,
                patterns=[
                    r"(?i)^#+\s*solution",
                    r"(?i)^#+\s*recommendation",
                    r"(?i)^#+\s*implementation",
                ],
                entity_focus=["Methodology", "Concept"],
                order=3,
            ),
            SectionTemplate(
                name="Outcome",
                optional=True,
                patterns=[
                    r"(?i)^#+\s*outcome",
                    r"(?i)^#+\s*result",
                    r"(?i)^#+\s*impact",
                ],
                entity_focus=["Finding"],
                order=4,
            ),
            SectionTemplate(
                name="Lessons Learned",
                optional=True,
                patterns=[
                    r"(?i)^#+\s*lessons?",
                    r"(?i)^#+\s*key\s*takeaway",
                    r"(?i)^#+\s*conclusion",
                ],
                entity_focus=["Finding"],
                order=5,
            ),
        ],
        entity_types=["Topic", "Concept", "Methodology", "Finding"],
        relationship_types=["APPLIES", "SOLVES", "DEMONSTRATES", "RELATED_TO"],
        extraction_prompts={
            "Background": "Extract context and background information.",
            "Problem": "Identify the core problem or challenge.",
            "Analysis": "Extract analytical approaches used.",
            "Solution": "Identify solutions and methodologies applied.",
            "Outcome": "Extract results and impacts achieved.",
            "Lessons Learned": "Identify key takeaways and conclusions.",
        },
    )


def _create_generic_template() -> ExtractionTemplate:
    """Create a generic fallback template."""
    return ExtractionTemplate(
        id="generic",
        name="Generic Document",
        description="Fallback template for documents that don't match specific types",
        template_type=TemplateType.GENERIC,
        document_patterns=[],  # Will match anything
        sections=[
            SectionTemplate(
                name="Content",
                optional=False,
                patterns=[r".*"],  # Match everything
                entity_focus=["Topic", "Concept", "Methodology", "Finding"],
                order=0,
            ),
        ],
        entity_types=["Topic", "Concept", "Methodology", "Finding"],
        relationship_types=["DEFINES", "DEPENDS_ON", "USES", "RELATED_TO"],
        extraction_prompts={
            "Content": "Extract all relevant entities and relationships.",
        },
    )


# ============================================================================
# TEMPLATE REGISTRY
# ============================================================================


class TemplateRegistry:
    """
    Registry for managing extraction templates.

    Provides methods for registering, retrieving, and detecting templates.
    Built-in templates are loaded at initialization.
    """

    def __init__(self):
        """Initialize registry with built-in templates."""
        self._templates: Dict[str, ExtractionTemplate] = {}
        self._load_builtin_templates()
        logger.info(f"TemplateRegistry initialized with {len(self._templates)} templates")

    def _load_builtin_templates(self) -> None:
        """Load all built-in templates."""
        builtin_creators = [
            _create_lecture_notes_template,
            _create_research_paper_template,
            _create_meeting_notes_template,
            _create_lab_report_template,
            _create_case_study_template,
            _create_generic_template,
        ]

        for creator in builtin_creators:
            template = creator()
            self._templates[template.id] = template
            logger.debug(f"Loaded built-in template: {template.id}")

    def register(self, template: ExtractionTemplate) -> None:
        """
        Register a new template.

        Args:
            template: Template to register

        Raises:
            ValueError: If template ID already exists and is built-in
        """
        if template.id in self._templates:
            existing = self._templates[template.id]
            if existing.is_builtin:
                raise ValueError(f"Cannot override built-in template: {template.id}")
            logger.warning(f"Overwriting custom template: {template.id}")

        self._templates[template.id] = template
        logger.info(f"Registered template: {template.id}")

    def get(self, template_id: str) -> Optional[ExtractionTemplate]:
        """
        Get a template by ID.

        Args:
            template_id: Template identifier

        Returns:
            Template if found, None otherwise
        """
        return self._templates.get(template_id)

    def list_all(self, include_custom: bool = True) -> List[ExtractionTemplate]:
        """
        List all available templates.

        Args:
            include_custom: Whether to include custom templates

        Returns:
            List of templates
        """
        templates = list(self._templates.values())
        if not include_custom:
            templates = [t for t in templates if t.is_builtin]
        return templates

    def detect_template(self, content: str) -> Tuple[ExtractionTemplate, float]:
        """
        Detect the best matching template for content.

        Analyzes document structure and patterns to determine the most
        appropriate template. Returns generic template if no good match found.

        Args:
            content: Document content to analyze

        Returns:
            Tuple of (best matching template, confidence score)
        """
        if not content or len(content.strip()) < 50:
            return self._templates["generic"], 0.0

        scores: List[Tuple[str, float]] = []

        for template_id, template in self._templates.items():
            if template_id == "generic":
                continue  # Skip generic for scoring

            score = self._score_template_match(content, template)
            scores.append((template_id, score))

        # Sort by score descending
        scores.sort(key=lambda x: x[1], reverse=True)

        if scores and scores[0][1] > 0.3:
            best_id = scores[0][0]
            best_score = scores[0][1]
            logger.info(f"Detected template: {best_id} (confidence: {best_score:.2f})")
            return self._templates[best_id], best_score
        else:
            logger.info("No template match found, using generic")
            return self._templates["generic"], 0.2

    def _score_template_match(
        self, content: str, template: ExtractionTemplate
    ) -> float:
        """
        Score how well content matches a template.

        Args:
            content: Document content
            template: Template to score against

        Returns:
            Match score between 0.0 and 1.0
        """
        score = 0.0
        max_score = 0.0

        # Score document patterns
        pattern_weight = 0.4
        max_score += pattern_weight
        pattern_matches = 0
        for pattern in template.document_patterns:
            try:
                if re.search(pattern, content, re.MULTILINE):
                    pattern_matches += 1
            except re.error:
                continue

        if template.document_patterns:
            pattern_ratio = pattern_matches / len(template.document_patterns)
            score += pattern_weight * min(pattern_ratio * 2, 1.0)

        # Score section patterns
        section_weight = 0.6
        max_score += section_weight
        required_sections = [s for s in template.sections if not s.optional]
        optional_sections = [s for s in template.sections if s.optional]

        required_found = 0
        optional_found = 0

        for section in required_sections:
            for pattern in section.patterns:
                try:
                    if re.search(pattern, content, re.MULTILINE):
                        required_found += 1
                        break
                except re.error:
                    continue

        for section in optional_sections:
            for pattern in section.patterns:
                try:
                    if re.search(pattern, content, re.MULTILINE):
                        optional_found += 1
                        break
                except re.error:
                    continue

        # Required sections have more weight
        if required_sections:
            required_ratio = required_found / len(required_sections)
            score += section_weight * 0.7 * required_ratio

        if optional_sections:
            optional_ratio = optional_found / len(optional_sections)
            score += section_weight * 0.3 * optional_ratio

        return min(score / max_score, 1.0) if max_score > 0 else 0.0

    def get_detection_alternatives(
        self, content: str, top_k: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Get alternative template matches with scores.

        Args:
            content: Document content
            top_k: Number of alternatives to return

        Returns:
            List of dicts with template_id, template_name, and confidence
        """
        scores: List[Tuple[str, float]] = []

        for template_id, template in self._templates.items():
            if template_id == "generic":
                continue
            score = self._score_template_match(content, template)
            scores.append((template_id, score))

        scores.sort(key=lambda x: x[1], reverse=True)

        return [
            {
                "template_id": tid,
                "template_name": self._templates[tid].name,
                "confidence": round(score, 3),
            }
            for tid, score in scores[:top_k]
        ]


# ============================================================================
# TEMPLATE EXTRACTOR
# ============================================================================


class TemplateExtractor:
    """
    Applies extraction templates to documents.

    Orchestrates template-based extraction by detecting sections,
    applying section-specific prompts, and computing quality scores.
    """

    def __init__(self, llm_client: Any = None, registry: TemplateRegistry = None):
        """
        Initialize template extractor.

        Args:
            llm_client: LLM client for extraction (optional)
            registry: Template registry (created if not provided)
        """
        self.llm_client = llm_client
        self.registry = registry or TemplateRegistry()
        logger.info("TemplateExtractor initialized")

    def extract_with_template(
        self,
        content: str,
        template_id: Optional[str] = None,
        options: Optional[ExtractionOptions] = None,
    ) -> TemplateExtractionResult:
        """
        Extract entities and relationships using a template.

        Args:
            content: Document content to extract from
            template_id: Template ID to use (None for auto-detection)
            options: Extraction options

        Returns:
            TemplateExtractionResult with extracted data
        """
        options = options or ExtractionOptions()

        # Get template (auto-detect if not specified)
        if template_id is None or template_id == "auto":
            template, detection_confidence = self.registry.detect_template(content)
        else:
            template = self.registry.get(template_id)
            if not template:
                logger.warning(f"Template not found: {template_id}, using generic")
                template = self.registry.get("generic")
            detection_confidence = 1.0 if template else 0.0

        # Detect sections in content
        detected_sections = self._detect_sections(content, template)
        sections_detected = [ds.section_template.name for ds in detected_sections]
        sections_missing = [
            s.name
            for s in template.sections
            if not s.optional and s.name not in sections_detected
        ]

        # Extract from each section
        section_results: List[SectionExtractionResult] = []
        all_entities: List[Dict[str, Any]] = []
        all_relationships: List[Dict[str, Any]] = []

        for detected_section in detected_sections:
            result = self._extract_section(
                detected_section, template, options
            )
            section_results.append(result)
            all_entities.extend(result.entities)
            all_relationships.extend(result.relationships)

        # Deduplicate entities
        all_entities = self._deduplicate_entities(all_entities)

        # Compute quality score
        quality_score = self._compute_quality_score(
            template=template,
            sections_detected=sections_detected,
            sections_missing=sections_missing,
            entities=all_entities,
            detection_confidence=detection_confidence,
        )

        return TemplateExtractionResult(
            template_id=template.id,
            template_name=template.name,
            sections_detected=sections_detected,
            sections_missing=sections_missing,
            section_results=section_results,
            entities=all_entities,
            relationships=all_relationships[:options.max_relationships],
            quality_score=quality_score,
        )

    def _detect_sections(
        self, content: str, template: ExtractionTemplate
    ) -> List[DetectedSection]:
        """
        Detect sections in document based on template patterns.

        Args:
            content: Document content
            template: Template with section definitions

        Returns:
            List of detected sections with positions and content
        """
        detected: List[DetectedSection] = []
        lines = content.split("\n")
        section_starts: List[Tuple[int, SectionTemplate, int]] = []

        # Find section starts
        for i, line in enumerate(lines):
            for section in template.sections:
                for pattern in section.patterns:
                    try:
                        if re.match(pattern, line.strip(), re.IGNORECASE):
                            # Calculate character position
                            char_pos = sum(len(lines[j]) + 1 for j in range(i))
                            section_starts.append((char_pos, section, i))
                            break
                    except re.error:
                        continue

        # Sort by position and remove duplicates for same section
        section_starts.sort(key=lambda x: x[0])
        seen_sections = set()
        unique_starts = []
        for start in section_starts:
            if start[1].name not in seen_sections:
                seen_sections.add(start[1].name)
                unique_starts.append(start)
        section_starts = unique_starts

        # Extract section content
        for i, (start_pos, section, start_line) in enumerate(section_starts):
            # End position is either next section start or end of document
            if i + 1 < len(section_starts):
                end_pos = section_starts[i + 1][0]
                end_line = section_starts[i + 1][2]
            else:
                end_pos = len(content)
                end_line = len(lines)

            # Extract content
            section_content = "\n".join(lines[start_line:end_line])

            detected.append(
                DetectedSection(
                    section_template=section,
                    start_pos=start_pos,
                    end_pos=end_pos,
                    content=section_content,
                    confidence=0.8 if section.optional else 0.9,
                )
            )

        # If no sections detected, treat whole content as single section
        if not detected and template.sections:
            first_section = template.sections[0]
            detected.append(
                DetectedSection(
                    section_template=first_section,
                    start_pos=0,
                    end_pos=len(content),
                    content=content,
                    confidence=0.5,
                )
            )

        return detected

    def _extract_section(
        self,
        detected_section: DetectedSection,
        template: ExtractionTemplate,
        options: ExtractionOptions,
    ) -> SectionExtractionResult:
        """
        Extract entities from a single section.

        Args:
            detected_section: Detected section with content
            template: Parent template
            options: Extraction options

        Returns:
            SectionExtractionResult with entities and relationships
        """
        section_name = detected_section.section_template.name
        content = detected_section.content
        entity_focus = detected_section.section_template.entity_focus

        # If no LLM client, use simple pattern-based extraction
        if not self.llm_client:
            entities = self._extract_entities_simple(
                content, entity_focus, options.max_entities_per_section
            )
            return SectionExtractionResult(
                section_name=section_name,
                entities=entities,
                relationships=[],
            )

        # Use LLM for extraction (implementation depends on llm_client interface)
        # This will be integrated with LLMEntityExtractor
        entities = self._extract_entities_simple(
            content, entity_focus, options.max_entities_per_section
        )

        return SectionExtractionResult(
            section_name=section_name,
            entities=entities,
            relationships=[],
        )

    def _extract_entities_simple(
        self, content: str, entity_focus: List[str], max_entities: int
    ) -> List[Dict[str, Any]]:
        """
        Simple pattern-based entity extraction fallback.

        Args:
            content: Section content
            entity_focus: Entity types to prioritize
            max_entities: Maximum entities to extract

        Returns:
            List of entity dicts
        """
        entities: List[Dict[str, Any]] = []

        # Extract capitalized terms as potential entities
        # This is a simple heuristic fallback
        words = content.split()
        seen = set()

        for i, word in enumerate(words):
            # Skip common words and short terms
            if len(word) < 3 or word.lower() in {"the", "and", "for", "with", "that"}:
                continue

            # Look for capitalized multi-word terms
            if word[0].isupper() and word not in seen:
                # Try to get the next word too for multi-word terms
                term = word
                if i + 1 < len(words) and words[i + 1][0].isupper():
                    term = f"{word} {words[i + 1]}"
                    seen.add(words[i + 1])

                seen.add(word)
                entity_type = entity_focus[0] if entity_focus else "Concept"

                entities.append({
                    "id": f"entity_{hashlib.md5(term.encode()).hexdigest()[:12]}",
                    "name": term,
                    "type": entity_type,
                    "definition": "",
                    "confidence": 0.5,
                    "source_section": "",
                })

                if len(entities) >= max_entities:
                    break

        return entities

    def _deduplicate_entities(
        self, entities: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Deduplicate entities by name (case-insensitive)."""
        seen: Dict[str, Dict[str, Any]] = {}
        for entity in entities:
            key = entity.get("name", "").lower().strip()
            if key and key not in seen:
                seen[key] = entity
            elif key in seen:
                # Keep higher confidence
                if entity.get("confidence", 0) > seen[key].get("confidence", 0):
                    seen[key] = entity
        return list(seen.values())

    def _compute_quality_score(
        self,
        template: ExtractionTemplate,
        sections_detected: List[str],
        sections_missing: List[str],
        entities: List[Dict[str, Any]],
        detection_confidence: float,
    ) -> float:
        """
        Compute quality score for template-based extraction.

        Args:
            template: Used template
            sections_detected: Detected section names
            sections_missing: Missing required section names
            entities: Extracted entities
            detection_confidence: Template detection confidence

        Returns:
            Quality score between 0.0 and 1.0
        """
        score = 0.0

        # Section coverage (40%)
        total_sections = len(template.sections)
        detected_count = len(sections_detected)
        if total_sections > 0:
            section_score = detected_count / total_sections
            # Penalize missing required sections
            penalty = len(sections_missing) * 0.1
            score += 0.4 * max(0, section_score - penalty)

        # Entity extraction (30%)
        if entities:
            # More entities generally indicates better extraction
            entity_score = min(len(entities) / 10, 1.0)
            score += 0.3 * entity_score

        # Template match confidence (30%)
        score += 0.3 * detection_confidence

        return min(max(score, 0.0), 1.0)


# ============================================================================
# SINGLETON INSTANCES
# ============================================================================

# Global registry instance
_template_registry: Optional[TemplateRegistry] = None


def get_template_registry() -> TemplateRegistry:
    """Get or create the global template registry."""
    global _template_registry
    if _template_registry is None:
        _template_registry = TemplateRegistry()
    return _template_registry


def get_template_extractor(llm_client: Any = None) -> TemplateExtractor:
    """Create a template extractor with shared registry."""
    return TemplateExtractor(
        llm_client=llm_client,
        registry=get_template_registry(),
    )
