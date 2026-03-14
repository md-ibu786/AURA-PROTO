"""
============================================================================
FILE: __init__.py
LOCATION: services/document_parsers/__init__.py
============================================================================

PURPOSE:
    Package initialization for specialized document parsers supporting different
    file formats with consistent interface and return types.

ROLE IN PROJECT:
    Document parsing module for AURA-NOTES-MANAGER.
    - Provides parsers for various document formats (DOCX, PDF, etc.)
    - Returns ParsedDocument objects with text, metadata, sections, and tables
    - Offers consistent parse() and parse_bytes() interface across all parsers

KEY COMPONENTS:
    - DocxParser: Microsoft Word document parser
    - ParsedDocument: Standardized output format with metadata
    - DocumentSection: Individual section within a parsed document
    - Exception classes: DocxParseError, CorruptedDocxError, etc.

DEPENDENCIES:
    - External: None (package init)
    - Internal: .docx_parser

USAGE:
    from services.document_parsers import DocxParser, ParsedDocument
    parser = DocxParser()
    document = parser.parse(file_path)
    print(document.text)
============================================================================
"""

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
