"""
Notes storage helpers
"""
try:
    from db import execute_one, PLACEHOLDER
except ImportError:
    from api.db import execute_one, PLACEHOLDER


def create_note_record(module_id: int, title: str, pdf_url: str):
    """Create a note record and return the created record."""
    query = f"""
        INSERT INTO notes (module_id, title, pdf_url)
        VALUES ({PLACEHOLDER}, {PLACEHOLDER}, {PLACEHOLDER})
        RETURNING id, module_id, title, pdf_url, created_at
    """
    return execute_one(query, (module_id, title, pdf_url))
