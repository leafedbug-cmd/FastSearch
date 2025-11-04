from __future__ import annotations

import sqlite3
from typing import Optional

from .db import connect


def upsert_doc_content(doc_id: int, content: str) -> None:
    # Replace existing row then insert new content
    with connect() as con:
        con.execute("DELETE FROM content_fts WHERE rowid=?", (doc_id,))
        con.execute("INSERT INTO content_fts(rowid, content) VALUES(?, ?)", (doc_id, content))


def delete_doc_content(doc_id: int) -> None:
    with connect() as con:
        con.execute("DELETE FROM content_fts WHERE rowid=?", (doc_id,))


def build_match_query(text: str) -> str:
    # Simple tokenizer: AND over whitespace tokens with prefix
    tokens = [t for t in text.strip().split() if t]
    if not tokens:
        return ""
    # Escape quotes
    toks = [t.replace('"', ' ') for t in tokens]
    return " ".join(f"{t}*" for t in toks)

