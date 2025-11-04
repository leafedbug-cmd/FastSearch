from __future__ import annotations

import os
import sqlite3
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT_DIR / "fastsearch_data"
DB_PATH = DATA_DIR / "fastsearch.db"


def ensure_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def connect(db_path: Path | str = DB_PATH) -> sqlite3.Connection:
    ensure_data_dir()
    con = sqlite3.connect(str(db_path))
    con.row_factory = sqlite3.Row
    # PRAGMAs tuned for desktop app speed
    pragmas = [
        ("journal_mode", "WAL"),
        ("synchronous", "NORMAL"),
        ("temp_store", "MEMORY"),
        ("mmap_size", 268435456),
        ("page_size", 4096),
        ("foreign_keys", 1),
    ]
    cur = con.cursor()
    for key, value in pragmas:
        cur.execute(f"PRAGMA {key}={value}")
    cur.close()
    return con


def initialize(db_path: Path | str = DB_PATH) -> None:
    ensure_data_dir()
    schema_path = Path(__file__).with_name("schema.sql")
    with connect(db_path) as con:
        with open(schema_path, "r", encoding="utf-8") as f:
            con.executescript(f.read())

