# ocr.py
# OCR service for extracting text from scanned documents and images

# Provides OCR text extraction supporting Tesseract (local, free) and
# Google Vision API (cloud, higher accuracy). Includes preprocessing
# pipeline with deskew and contrast enhancement, and produces KG-ready
# documents for integration with the knowledge graph pipeline.

# @see: base.py - OCRProcessor abstract base class
# @see: config.py - MultimodalConfig for provider settings
# @note: Methods raise NotImplementedError - full implementation in future phase

from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field

from .base import (
    BoundingBox,
    OCRProcessor,
    OCRResult,
    ProcessConfig,
    ProcessResult,
)


class OCRPageContent(BaseModel):
    """Single page OCR result."""

    page_number: int
    text: str
    confidence: float
    bounding_boxes: List[BoundingBox] = Field(default_factory=list)
    is_scanned: bool


class KGReadyOCRDocument(BaseModel):
    """OCR document prepared for KG pipeline ingestion."""

    document_id: str
    module_id: str
    title: str
    pages: List[OCRPageContent]
    total_pages: int
    scanned_pages: List[int]
    ocr_provider: str
    average_confidence: float
    created_at: datetime
    metadata: Dict[str, Any] = Field(default_factory=dict)


class OCRService(OCRProcessor):
    """
    OCR service for extracting text from scanned documents and images.

    Supports Tesseract (local, free) and Google Vision API (cloud, higher
    accuracy). Automatically detects which PDF pages need OCR vs already
    have a text layer.

    Attributes:
        provider: OCR provider name ("tesseract" or "google_vision").
        languages: List of language codes for OCR (e.g., ["eng", "fra"]).
    """

    def __init__(
        self,
        provider: str = "tesseract",
        google_credentials_path: Optional[str] = None,
        tesseract_path: Optional[str] = None,
        languages: Optional[List[str]] = None,
    ) -> None:
        """
        Initialize the OCR service.

        Args:
            provider: OCR provider ("tesseract" or "google_vision").
            google_credentials_path: Path to Google Cloud credentials JSON.
            tesseract_path: Path to Tesseract executable.
            languages: List of language codes (default: ["eng"]).
        """
        self.provider = provider
        self.languages = languages or ["eng"]
        self._init_provider(google_credentials_path, tesseract_path)

    def _init_provider(
        self, google_credentials_path: Optional[str], tesseract_path: Optional[str]
    ) -> None:
        """Initialize the selected OCR provider."""
        # Stub - provider initialization in future phase
        self._google_credentials = google_credentials_path
        self._tesseract_path = tesseract_path

    def supported_formats(self) -> List[str]:
        """Return list of supported image/document formats."""
        return ["pdf", "png", "jpg", "jpeg", "tiff", "bmp", "gif"]

    async def process(
        self, source: Union[str, bytes], config: ProcessConfig
    ) -> ProcessResult:
        """
        Process image/document content and return structured result.

        Args:
            source: File path or raw image bytes.
            config: Processing configuration options.

        Returns:
            ProcessResult with extracted text.

        Raises:
            NotImplementedError: Full implementation in future multimodal phase.
        """
        raise NotImplementedError("Full implementation in future multimodal phase")

    async def extract_text(
        self, image_source: Union[str, bytes], enhance: bool = True
    ) -> OCRResult:
        """
        Extract text from single image.

        Args:
            image_source: File path or image bytes.
            enhance: Apply preprocessing (deskew, contrast) before OCR.

        Returns:
            OCRResult with extracted text and bounding boxes.

        Raises:
            NotImplementedError: Full implementation in future multimodal phase.
        """
        raise NotImplementedError("Full implementation in future multimodal phase")

    async def extract_from_pdf(
        self, pdf_path: str, pages: Optional[List[int]] = None, dpi: int = 300
    ) -> List[OCRResult]:
        """
        Extract text from PDF pages (scanned or mixed).

        Detects which pages need OCR vs already have text layer.

        Args:
            pdf_path: Path to PDF file.
            pages: Optional list of page numbers to process (0-indexed).
            dpi: Resolution for rendering PDF pages as images.

        Returns:
            List of OCRResult, one per processed page.

        Raises:
            NotImplementedError: Full implementation in future multimodal phase.
        """
        raise NotImplementedError("Full implementation in future multimodal phase")

    async def extract_for_kg(
        self, document_path: str, module_id: str, document_title: str
    ) -> KGReadyOCRDocument:
        """
        Extract and prepare OCR content for KG ingestion.

        Returns structured document ready for chunking and entity extraction.

        Args:
            document_path: Path to PDF or image file.
            module_id: Module ID for KG association.
            document_title: Title for the document.

        Returns:
            KGReadyOCRDocument ready for KG pipeline.

        Raises:
            NotImplementedError: Full implementation in future multimodal phase.
        """
        raise NotImplementedError("Full implementation in future multimodal phase")

    async def health_check(self) -> bool:
        """
        Check if OCR provider is available.

        Returns:
            True if the configured provider is ready.
        """
        # Stub - returns False until configured
        return False

    def _detect_scanned_pages(self, pdf_path: str) -> List[int]:
        """
        Identify which PDF pages are scanned (no text layer).

        Uses pdfminer or PyMuPDF to check text content per page.

        Args:
            pdf_path: Path to PDF file.

        Returns:
            List of page numbers (0-indexed) that are scanned.

        Raises:
            NotImplementedError: Full implementation in future multimodal phase.
        """
        raise NotImplementedError("Full implementation in future multimodal phase")
