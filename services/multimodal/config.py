# config.py
# Configuration for multimodal processing services

# Centralized configuration for all multimodal providers including
# audio transcription (Deepgram/Whisper), OCR (Tesseract/Google Vision),
# and image processing (Gemini Vision). Uses pydantic-settings for
# environment variable loading with sensible defaults.

# @see: audio.py, ocr.py, image.py - Services that consume this config
# @note: Set MULTIMODAL_* environment variables to override defaults

from enum import Enum
from typing import List, Optional

from pydantic_settings import BaseSettings


class AudioProvider(str, Enum):
    """Supported audio transcription providers."""

    DEEPGRAM = "deepgram"
    WHISPER = "whisper"
    WHISPER_API = "whisper_api"


class OCRProvider(str, Enum):
    """Supported OCR providers."""

    TESSERACT = "tesseract"
    GOOGLE_VISION = "google_vision"
    AZURE_VISION = "azure_vision"


class MultimodalConfig(BaseSettings):
    """
    Configuration for multimodal processing services.

    All settings can be overridden via environment variables with
    the MULTIMODAL_ prefix (e.g., MULTIMODAL_AUDIO_PROVIDER=whisper).
    """

    # -------------------------------------------------------------------------
    # Audio Transcription Settings
    # -------------------------------------------------------------------------
    audio_provider: AudioProvider = AudioProvider.DEEPGRAM
    deepgram_api_key: Optional[str] = None
    whisper_model: str = "base"  # tiny, base, small, medium, large
    whisper_device: str = "cpu"  # cpu, cuda
    audio_languages: List[str] = ["en"]
    enable_diarization: bool = True

    # -------------------------------------------------------------------------
    # OCR Settings
    # -------------------------------------------------------------------------
    ocr_provider: OCRProvider = OCRProvider.TESSERACT
    tesseract_path: Optional[str] = None
    google_vision_credentials: Optional[str] = None
    ocr_languages: List[str] = ["eng"]
    ocr_dpi: int = 300
    ocr_enhance_images: bool = True

    # -------------------------------------------------------------------------
    # Image Extraction Settings
    # -------------------------------------------------------------------------
    enable_image_extraction: bool = True
    min_image_width: int = 100
    min_image_height: int = 100
    enable_image_descriptions: bool = True
    gemini_api_key: Optional[str] = None

    # -------------------------------------------------------------------------
    # Multimodal Embeddings (future)
    # -------------------------------------------------------------------------
    enable_multimodal_embeddings: bool = False
    clip_model: str = "openai/clip-vit-base-patch32"

    # -------------------------------------------------------------------------
    # Processing Limits
    # -------------------------------------------------------------------------
    max_audio_duration_seconds: int = 7200  # 2 hours
    max_pdf_pages_ocr: int = 100
    async_processing_threshold_mb: int = 50  # Files larger use async

    # -------------------------------------------------------------------------
    # Storage Paths
    # -------------------------------------------------------------------------
    extracted_images_path: str = "data/extracted_images"
    transcripts_path: str = "data/transcripts"

    model_config = {
        "env_prefix": "MULTIMODAL_",
        "env_file": ".env",
        "extra": "ignore",
    }


# Module-level singleton instance
_config_instance: Optional[MultimodalConfig] = None


def get_multimodal_config() -> MultimodalConfig:
    """
    Get multimodal configuration singleton.

    Returns:
        MultimodalConfig instance with settings loaded from environment.
    """
    global _config_instance
    if _config_instance is None:
        _config_instance = MultimodalConfig()
    return _config_instance
