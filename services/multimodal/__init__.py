"""
============================================================================
FILE: __init__.py
LOCATION: services/multimodal/__init__.py
============================================================================

PURPOSE:
    Package initialization for multimodal content processing services providing
    unified audio, OCR, and image processing capabilities.

ROLE IN PROJECT:
    Entry point for the multimodal processing pipeline in AURA-NOTES-MANAGER.
    - Exports all base classes, service implementations, and configuration
    - Provides convenient imports for audio transcription, OCR, and image analysis
    - Coordinates multimodal services for KG pipeline integration

KEY COMPONENTS:
    - AudioIngestionService, KGReadyTranscript: Audio processing
    - OCRService, KGReadyOCRDocument: OCR text extraction
    - ImageExtractionService, KGReadyImage: Image analysis
    - MultimodalDocumentProcessor, MultimodalConfig: Unified processing

DEPENDENCIES:
    - External: None (package init)
    - Internal: .audio, .base, .config, .image, .ocr, .processor

USAGE:
    from services.multimodal import (
        MultimodalDocumentProcessor,
        MultimodalConfig,
        AudioIngestionService,
        OCRService,
        ImageExtractionService,
    )
============================================================================
"""

from .audio import AudioIngestionService, KGReadyTranscript
from .base import (
    AudioProcessor,
    BoundingBox,
    DiagramInfo,
    ImageDescription,
    ImageProcessor,
    MultimodalProcessor,
    OCRProcessor,
    OCRResult,
    ProcessConfig,
    ProcessResult,
    TranscriptionResult,
    TranscriptionSegment,
    WordTimestamp,
)
from .config import (
    AudioProvider,
    MultimodalConfig,
    OCRProvider,
    get_multimodal_config,
)
from .image import ImageExtractionService, KGReadyImage
from .ocr import KGReadyOCRDocument, OCRPageContent, OCRService
from .processor import (
    ContentType,
    DocumentSection,
    MultimodalDocument,
    MultimodalDocumentProcessor,
    ProcessingOptions,
)

__all__ = [
    # Base classes
    "MultimodalProcessor",
    "AudioProcessor",
    "OCRProcessor",
    "ImageProcessor",
    # Configuration
    "MultimodalConfig",
    "AudioProvider",
    "OCRProvider",
    "get_multimodal_config",
    # Services
    "AudioIngestionService",
    "OCRService",
    "ImageExtractionService",
    "MultimodalDocumentProcessor",
    # Data models - Base
    "ProcessConfig",
    "ProcessResult",
    "TranscriptionResult",
    "TranscriptionSegment",
    "WordTimestamp",
    "OCRResult",
    "BoundingBox",
    "DiagramInfo",
    "ImageDescription",
    # Data models - KG Ready
    "KGReadyTranscript",
    "KGReadyOCRDocument",
    "OCRPageContent",
    "KGReadyImage",
    # Processor models
    "ContentType",
    "ProcessingOptions",
    "DocumentSection",
    "MultimodalDocument",
]
