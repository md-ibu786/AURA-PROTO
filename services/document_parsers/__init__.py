# __init__.py
# Document parsers package initialization

# This package contains specialized document parsers for different file formats.
# Each parser provides consistent interface (parse, parse_bytes) and returns
# ParsedDocument objects with text, metadata, sections, and tables.

# @see: docx_parser.py - Microsoft Word document parser
# @note: Add new parsers here as import for easy access

from .docx_parser import (
    DocxParser,
    ParsedDocument,
    DocumentSection,
    DocxParseError,
    CorruptedDocxError,
    PasswordProtectedDocxError,
    EmptyDocxError,
)

__all__ = [
    "DocxParser",
    "ParsedDocument",
    "DocumentSection",
    "DocxParseError",
    "CorruptedDocxError",
    "PasswordProtectedDocxError",
    "EmptyDocxError",
]
