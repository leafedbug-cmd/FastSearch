from __future__ import annotations

import os
import sqlite3
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from .db import DB_PATH, connect


EXT_FILETYPE: Dict[str, str] = {
    # Documents
    ".pdf": "PDF",
    ".doc": "Document", ".docx": "Document", ".odt": "Document", ".rtf": "Document",
    ".txt": "Document", ".md": "Document",
    # Spreadsheets
    ".xls": "Spreadsheet", ".xlsx": "Spreadsheet", ".csv": "Spreadsheet", ".ods": "Spreadsheet",
    # Presentations
    ".ppt": "Presentation", ".pptx": "Presentation", ".odp": "Presentation",
    # Images
    ".png": "Image", ".jpg": "Image", ".jpeg": "Image", ".gif": "Image", ".bmp": "Image", ".tiff": "Image",
    # Code
    ".py": "Code", ".js": "Code", ".ts": "Code", ".java": "Code", ".cs": "Code", ".cpp": "Code", ".c": "Code",
    ".h": "Code", ".hpp": "Code", ".go": "Code", ".rs": "Code", ".rb": "Code", ".php": "Code", ".sh": "Code",
    ".ps1": "Code", ".json": "Code", ".yml": "Code", ".yaml": "Code", ".xml": "Code",
    # Archives
    ".zip": "Archive", ".7z": "Archive", ".rar": "Archive", ".tar": "Archive", ".gz": "Archive",
}


SIZE_BUCKETS = ["<1MB", "1–100MB", ">100MB"]
DATE_BUCKETS = ["Today", "This Week", "This Month", "This Year", "Older"]


def classify_filetype(ext: str) -> str:
    return EXT_FILETYPE.get(ext.lower(), "Other")


def size_bucket(size_bytes: int) -> str:
    mb = 1024 * 1024
    if size_bytes < 1 * mb:
        return "<1MB"
    if size_bytes <= 100 * mb:
        return "1–100MB"
    return ">100MB"


def date_bucket(mtime_ns: int) -> str:
    dt = datetime.fromtimestamp(mtime_ns / 1e9)
    now = datetime.now()
    delta = now - dt
    if dt.date() == now.date():
        return "Today"
    if delta <= timedelta(days=7):
        return "This Week"
    if delta <= timedelta(days=31):
        return "This Month"
    if dt.year == now.year:
        return "This Year"
    return "Older"


def normalize_name(name: str) -> str:
    return name.lower()


@dataclass
class SearchFilters:
    filetypes: Sequence[str] | None = None
    size_buckets: Sequence[str] | None = None
    date_buckets: Sequence[str] | None = None
    location_ids: Sequence[int] | None = None


class DocsRepo:
    def __init__(self, db_path: Path = DB_PATH) -> None:
        self.db_path = db_path

    def _connect(self) -> sqlite3.Connection:
        return connect(self.db_path)

    # Locations map: string path → id
    def ensure_location(self, con: sqlite3.Connection, path: str) -> int:
        cur = con.execute("SELECT id FROM locations WHERE path=?", (path,))
        row = cur.fetchone()
        if row:
            return int(row[0])
        cur = con.execute("INSERT INTO locations(path) VALUES(?)", (path,))
        return int(cur.lastrowid)

    def upsert_file(self, path: Path, root_locations: Sequence[Path]) -> Optional[int]:
        try:
            st = path.stat()
        except FileNotFoundError:
            return None
        except PermissionError:
            return None

        name = path.name
        parent = str(path.parent)
        ext = path.suffix.lower()
        ft = classify_filetype(ext)
        sb = size_bucket(st.st_size)
        mbucket = date_bucket(int(st.st_mtime_ns))
        name_norm = normalize_name(name)

        # Pick closest matching root as location, else parent
        location_path = None
        s_path = str(path)
        for root in sorted(root_locations, key=lambda p: -len(str(p))):
            if s_path.startswith(str(root)):
                location_path = str(root)
                break
        if location_path is None:
            location_path = parent

        with self._connect() as con:
            loc_id = self.ensure_location(con, location_path)
            con.execute(
                """
                INSERT INTO docs(path, name, name_norm, parent, ext, size_bytes, mtime_ns, ctime_ns,
                                 filetype, size_bucket, date_bucket, location_id, deleted)
                VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
                ON CONFLICT(path) DO UPDATE SET
                  name=excluded.name,
                  name_norm=excluded.name_norm,
                  parent=excluded.parent,
                  ext=excluded.ext,
                  size_bytes=excluded.size_bytes,
                  mtime_ns=excluded.mtime_ns,
                  ctime_ns=excluded.ctime_ns,
                  filetype=excluded.filetype,
                  size_bucket=excluded.size_bucket,
                  date_bucket=excluded.date_bucket,
                  location_id=excluded.location_id,
                  deleted=0
                """,
                (
                    str(path), name, name_norm, parent, ext,
                    int(st.st_size), int(st.st_mtime_ns), int(st.st_ctime_ns),
                    ft, sb, mbucket, loc_id,
                ),
            )
            cur = con.execute("SELECT id FROM docs WHERE path=?", (str(path),))
            row = cur.fetchone()
            return int(row[0]) if row else None

    def mark_deleted(self, path: Path) -> None:
        with self._connect() as con:
            con.execute("UPDATE docs SET deleted=1 WHERE path=?", (str(path),))

    def location_ids_for_paths(self, paths: Sequence[str]) -> List[int]:
        if not paths:
            return []
        with self._connect() as con:
            placeholders = ",".join(["?"] * len(paths))
            cur = con.execute(
                f"SELECT id FROM locations WHERE path IN ({placeholders})",
                list(paths),
            )
            return [int(r[0]) for r in cur.fetchall()]

    def count_docs_for_location_paths(self, paths: Sequence[str]) -> int:
        if not paths:
            return 0
        with self._connect() as con:
            placeholders = ",".join(["?"] * len(paths))
            cur = con.execute(
                f"SELECT COUNT(*) FROM docs WHERE deleted=0 AND location_id IN (SELECT id FROM locations WHERE path IN ({placeholders}))",
                list(paths),
            )
            row = cur.fetchone()
            return int(row[0]) if row else 0

    def search(self, query: str, filters: SearchFilters, limit: int = 500) -> Tuple[List[sqlite3.Row], Dict[str, Dict[str, int]]]:
        q = (query or "").strip()
        where = ["docs.deleted=0"]
        params: List[object] = []

        if q:
            like = f"%{q.lower()}%"
            where.append("(LOWER(docs.name) LIKE ? OR LOWER(docs.path) LIKE ?)")
            params.extend([like, like])

        def add_in(field: str, values: Optional[Sequence[object]]):
            nonlocal where, params
            if values:
                if "." not in field:
                    field = f"docs.{field}"
                placeholders = ",".join(["?"] * len(values))
                where.append(f"{field} IN ({placeholders})")
                params.extend(values)

        add_in("filetype", filters.filetypes)
        add_in("size_bucket", filters.size_buckets)
        add_in("date_bucket", filters.date_buckets)
        add_in("location_id", filters.location_ids)

        where_sql = " AND ".join(where) if where else "1"

        order_sql = (
            "CASE WHEN LOWER(docs.name) LIKE ? THEN 0 ELSE 1 END, docs.mtime_ns DESC"
            if q else "docs.mtime_ns DESC"
        )
        order_params: List[object] = [f"%{q.lower()}%"] if q else []

        base_sql = (
            "SELECT docs.*, locations.path AS location_path "
            "FROM docs LEFT JOIN locations ON locations.id = docs.location_id "
            f"WHERE {where_sql} ORDER BY {order_sql} LIMIT ?"
        )
        rows: List[sqlite3.Row]
        with self._connect() as con:
            con.execute("PRAGMA query_only=1")
            cur = con.execute(base_sql, (*params, *order_params, limit))
            rows = cur.fetchall()

            # Facets over the same candidate filter
            facets: Dict[str, Dict[str, int]] = {}

            def facet_counts(column: str, table: str = "docs") -> Dict[str, int]:
                cur2 = con.execute(
                    f"SELECT {column}, COUNT(*) as c FROM {table} WHERE {where_sql} GROUP BY {column}",
                    params,
                )
                out: Dict[str, int] = {}
                for r in cur2.fetchall():
                    key = r[0]
                    key = str(key) if key is not None else ""
                    out[key] = int(r[1])
                return out

            facets["filetype"] = facet_counts("filetype")
            facets["size_bucket"] = facet_counts("size_bucket")
            facets["date_bucket"] = facet_counts("date_bucket")

            # Location names lookup
            loc_counts: Dict[str, int] = {}
            cur = con.execute(
                f"SELECT location_id, COUNT(*) FROM docs WHERE {where_sql} GROUP BY location_id",
                params,
            )
            id_to_count = {int(r[0]): int(r[1]) for r in cur.fetchall() if r[0] is not None}
            if id_to_count:
                ids = tuple(id_to_count.keys())
                placeholders = ",".join(["?"] * len(ids))
                cur = con.execute(
                    f"SELECT id, path FROM locations WHERE id IN ({placeholders})",
                    ids,
                )
                for r in cur.fetchall():
                    loc_counts[str(r[1])] = id_to_count.get(int(r[0]), 0)
            facets["location"] = loc_counts

        return rows, facets
