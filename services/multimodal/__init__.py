# __init__.py
# Multimodal service package for audio, OCR, and image processing

# Provides unified multimodal content processing capabilities for the
# AURA-NOTES-MANAGER KG pipeline. Includes abstract base classes, concrete
# service implementations (stubs), configuration, and the unified processor
# for coordinating all multimodal services.

# @see: processor.py - Main entry point for document processing
# @note: All services are stubs - full implementation in future multimodal phase

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
