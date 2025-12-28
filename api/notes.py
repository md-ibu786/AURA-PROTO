"""
Notes storage helpers
"""
try:
    from db import execute_write, execute_one
except ImportError:
    from api.db import execute_write, execute_one


def create_note_record(module_id: int, title: str, pdf_url: str):
    query = """
        INSERT INTO notes (module_id, title, pdf_url)
        VALUES (?, ?, ?)
        RETURNING id, module_id, title, pdf_url, created_at
    """
    # For SQLite conn.cursor().lastrowid may be needed; use execute_write then fetch
    new_id = execute_write("INSERT INTO notes (module_id, title, pdf_url) VALUES (?, ?, ?)", (module_id, title, pdf_url))
    if not new_id:
        return None
    return execute_one("SELECT id, module_id, title, pdf_url, created_at FROM notes WHERE id = ?", (new_id,))

