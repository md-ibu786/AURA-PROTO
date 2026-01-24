# processor.py
# Unified multimodal document processor for KG pipeline integration

# Provides a single entry point for processing any multimodal content into
# KG-ready format. Coordinates audio transcription, OCR text extraction,
# and image/diagram analysis services to produce unified documents ready
# for entity extraction and knowledge graph ingestion.

# @see: audio.py, ocr.py, image.py - Individual service implementations
# @see: config.py - MultimodalConfig for provider settings
# @note: Methods raise NotImplementedError - full implementation in future phase

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field

from .audio import AudioIngestionService, KGReadyTranscript
from .config import MultimodalConfig, get_multimodal_config
from .image import ImageExtractionService, KGReadyImage
from .ocr import KGReadyOCRDocument, OCRService


class ContentType(str, Enum):
    """Type of content detected in a document."""

    TEXT_DOCUMENT = "text_document"  # Standard text extraction
    SCANNED_DOCUMENT = "scanned_document"  # Needs OCR
    AUDIO = "audio"  # Needs transcription
    VIDEO = "video"  # Needs transcription + frame extraction
    IMAGE = "image"  # Standalone image
    MIXED = "mixed"  # Multiple types


class ProcessingOptions(BaseModel):
    """Options for multimodal processing."""

    enable_ocr: bool = True
    enable_image_extraction: bool = True
    enable_image_descriptions: bool = True
    ocr_languages: List[str] = Field(default_factory=lambda: ["eng"])
    audio_language: str = "en"
    enable_diarization: bool = True
    async_processing: bool = False


class DocumentSection(BaseModel):
    """Section of multimodal document."""

    section_id: str
    section_type: str  # text, transcript_segment, ocr_page, image_description
    content: str
    start_offset: int
    end_offset: int
    source: str  # original, transcribed, ocr, image_description
    confidence: Optional[float] = None


class MultimodalDocument(BaseModel):
    """Result of multimodal processing, ready for KG ingestion."""

    document_id: str
    module_id: str
    title: str
    content_type: ContentType
    text_content: str
    sections: List[DocumentSection] = Field(default_factory=list)
    images: List[KGReadyImage] = Field(default_factory=list)
    transcript: Optional[KGReadyTranscript] = None
    ocr_result: Optional[KGReadyOCRDocument] = None
    processing_time_seconds: float
    created_at: datetime
    metadata: Dict[str, Any] = Field(default_factory=dict)


class MultimodalDocumentProcessor:
    """
    Unified processor for multimodal content integration with KG pipeline.

    Coordinates audio, OCR, and image services to produce KG-ready documents.
    Automatically detects content type and applies appropriate processing.

    Usage with kg_processor.py:
    ```python
    multimodal = MultimodalDocumentProcessor(get_multimodal_config())
    content_type = multimodal.detect_content_type(file_path)

    if content_type in [ContentType.AUDIO, ContentType.SCANNED_DOCUMENT]:
        mm_doc = await multimodal.process_document(file_path, module_id, title)
        text = mm_doc.text_content
        # Continue with standard KG processing using extracted text
    ```

    Attributes:
        config: Multimodal configuration settings.
        audio: Audio transcription service.
        ocr: OCR text extraction service.
        image: Image extraction and analysis service.
    """

    def __init__(
        self,
        config: Optional[MultimodalConfig] = None,
        audio_service: Optional[AudioIngestionService] = None,
        ocr_service: Optional[OCRService] = None,
        image_service: Optional[ImageExtractionService] = None,
    ) -> None:
        """
        Initialize the multimodal document processor.

        Args:
            config: Multimodal configuration (uses default if not provided).
            audio_service: Audio transcription service instance.
            ocr_service: OCR text extraction service instance.
            image_service: Image extraction service instance.
        """
        self.config = config or get_multimodal_config()
        self.audio = audio_service or AudioIngestionService(
            deepgram_api_key=self.config.deepgram_api_key,
            whisper_model=self.config.whisper_model,
            prefer_provider=self.config.audio_provider.value,
        )
        self.ocr = ocr_service or OCRService(
            provider=self.config.ocr_provider.value,
            google_credentials_path=self.config.google_vision_credentials,
            tesseract_path=self.config.tesseract_path,
            languages=self.config.ocr_languages,
        )
        self.image = image_service or ImageExtractionService(
            gemini_api_key=self.config.gemini_api_key,
            min_image_size=(self.config.min_image_width, self.config.min_image_height),
            extract_embedded=self.config.enable_image_extraction,
        )

    async def process_document(
        self,
        source_path: str,
        module_id: str,
        document_title: str,
        options: Optional[ProcessingOptions] = None,
    ) -> MultimodalDocument:
        """
        Process any supported document type into KG-ready format.

        Automatically detects content type and applies appropriate processing:
        - Audio files: Transcribe to text
        - Scanned PDFs: OCR to extract text
        - Documents with images: Extract and describe diagrams

        Args:
            source_path: Path to the source file.
            module_id: Module ID for KG association.
            document_title: Title for the document.
            options: Optional processing options.

        Returns:
            MultimodalDocument ready for KG ingestion.

        Raises:
            NotImplementedError: Full implementation in future multimodal phase.
        """
        raise NotImplementedError("Full implementation in future multimodal phase")

    async def process_audio(
        self, audio_path: str, module_id: str, document_title: str
    ) -> MultimodalDocument:
        """
        Process audio file specifically.

        Args:
            audio_path: Path to audio file.
            module_id: Module ID for KG association.
            document_title: Title for the document.

        Returns:
            MultimodalDocument with transcribed content.

        Raises:
            NotImplementedError: Full implementation in future multimodal phase.
        """
        raise NotImplementedError("Full implementation in future multimodal phase")

    async def process_scanned_pdf(
        self, pdf_path: str, module_id: str, document_title: str
    ) -> MultimodalDocument:
        """
        Process scanned PDF with OCR.

        Args:
            pdf_path: Path to PDF file.
            module_id: Module ID for KG association.
            document_title: Title for the document.

        Returns:
            MultimodalDocument with OCR-extracted content.

        Raises:
            NotImplementedError: Full implementation in future multimodal phase.
        """
        raise NotImplementedError("Full implementation in future multimodal phase")

    async def extract_document_images(
        self, document_path: str, module_id: str
    ) -> List[KGReadyImage]:
        """
        Extract all images from document.

        Args:
            document_path: Path to document file.
            module_id: Module ID for KG association.

        Returns:
            List of KGReadyImage extracted from document.

        Raises:
            NotImplementedError: Full implementation in future multimodal phase.
        """
        raise NotImplementedError("Full implementation in future multimodal phase")

    def detect_content_type(self, file_path: str) -> ContentType:
        """
        Detect whether file needs audio, OCR, or standard processing.

        Checks file extension and, for PDFs, whether pages are scanned.

        Args:
            file_path: Path to file.

        Returns:
            ContentType indicating the processing approach needed.

        Raises:
            NotImplementedError: Full implementation in future multimodal phase.
        """
        raise NotImplementedError("Full implementation in future multimodal phase")
