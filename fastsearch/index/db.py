from __future__ import annotations

import shutil
import sqlite3
from pathlib import Path

try:
    from platformdirs import user_data_dir
except ModuleNotFoundError:  # pragma: no cover
    def user_data_dir(app_name: str, app_author: str) -> str:
        return str(Path.home() / f".{app_name.lower()}")


ROOT_DIR = Path(__file__).resolve().parents[2]
APP_NAME = "FastSearch"
APP_AUTHOR = "FastSearch"
DATA_DIR = Path(user_data_dir(APP_NAME, APP_AUTHOR))
LEGACY_DATA_DIR = ROOT_DIR / "fastsearch_data"
DB_PATH = DATA_DIR / "fastsearch.db"


def ensure_data_dir() -> None:
    _migrate_legacy_data_dir()
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def _migrate_legacy_data_dir() -> None:
    if not LEGACY_DATA_DIR.exists():
        return
    DATA_DIR.parent.mkdir(parents=True, exist_ok=True)
    if not DATA_DIR.exists():
        shutil.move(str(LEGACY_DATA_DIR), str(DATA_DIR))
        return
    for item in LEGACY_DATA_DIR.iterdir():
        target = DATA_DIR / item.name
        if target.exists():
            continue
        shutil.move(str(item), str(target))
    shutil.rmtree(LEGACY_DATA_DIR, ignore_errors=True)


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
        _migrate(con)


def _migrate(con: sqlite3.Connection) -> None:
    # Add columns to locations for scan state if missing
    cur = con.execute("PRAGMA table_info(locations)")
    cols = {row[1] for row in cur.fetchall()}  # name is at index 1
    to_add = []
    if "initial_scan_complete" not in cols:
        to_add.append("ALTER TABLE locations ADD COLUMN initial_scan_complete INTEGER NOT NULL DEFAULT 0")
    if "last_scan_ts" not in cols:
        to_add.append("ALTER TABLE locations ADD COLUMN last_scan_ts INTEGER NOT NULL DEFAULT 0")
    if "last_scan_count" not in cols:
        to_add.append("ALTER TABLE locations ADD COLUMN last_scan_count INTEGER NOT NULL DEFAULT 0")
    for stmt in to_add:
        con.execute(stmt)
