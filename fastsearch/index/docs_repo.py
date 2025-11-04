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
        cur = con.execute("INSERT INTO locations(path, initial_scan_complete, last_scan_ts, last_scan_count) VALUES(?, 0, 0, 0)", (path,))
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
            return self._upsert_file_with_con(con, path, root_locations, location_path, name, name_norm, parent, ext, st, ft, sb, mbucket)

    def _upsert_file_with_con(
        self,
        con: sqlite3.Connection,
        path: Path,
        root_locations: Sequence[Path],
        location_path: str,
        name: str,
        name_norm: str,
        parent: str,
        ext: str,
        st,
        ft: str,
        sb: str,
        mbucket: str,
    ) -> Optional[int]:
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
            cur = con.execute("SELECT id FROM docs WHERE path=?", (str(path),))
            row = cur.fetchone()
            if row:
                doc_id = int(row[0])
                con.execute("UPDATE docs SET deleted=1 WHERE id=?", (doc_id,))
                try:
                    con.execute("DELETE FROM content_fts WHERE rowid=?", (doc_id,))
                except Exception:
                    pass

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

    def is_initial_scan_complete(self, path: str) -> bool:
        with self._connect() as con:
            cur = con.execute("SELECT initial_scan_complete FROM locations WHERE path=?", (path,))
            row = cur.fetchone()
            if not row:
                return False
            return bool(int(row[0]))

    def update_location_scan_state(self, path: str, *, complete: bool | None = None, last_scan_count: int | None = None) -> None:
        now = int(time.time())
        sets = ["last_scan_ts=?"]
        params: List[object] = [now]
        if complete is not None:
            sets.append("initial_scan_complete=?")
            params.append(1 if complete else 0)
        if last_scan_count is not None:
            sets.append("last_scan_count=?")
            params.append(int(last_scan_count))
        sets_sql = ", ".join(sets)
        with self._connect() as con:
            # Ensure exists
            self.ensure_location(con, path)
            params.append(path)
            con.execute(f"UPDATE locations SET {sets_sql} WHERE path=?", params)

    def iter_paths_missing_content(self, roots: Sequence[Path], batch: int = 5000):
        if not roots:
            return []
        root_strs = [str(p) for p in roots]
        with self._connect() as con:
            placeholders = ",".join(["?"] * len(root_strs))
            sql = (
                "SELECT docs.path FROM docs "
                "LEFT JOIN content_fts ON content_fts.rowid = docs.id "
                f"WHERE docs.deleted=0 AND content_fts.rowid IS NULL AND docs.location_id IN (SELECT id FROM locations WHERE path IN ({placeholders})) "
                "LIMIT ?"
            )
            cur = con.execute(sql, (*root_strs, batch))
            return [Path(r[0]) for r in cur.fetchall()]

    def search(self, query: str, filters: SearchFilters, limit: int = 500, mode: str = "all") -> Tuple[List[sqlite3.Row], Dict[str, Dict[str, int]]]:
        q = (query or "").strip()
        params: List[object] = []

        # Filters
        flt = ["docs.deleted=0"]

        def add_in(field: str, values: Optional[Sequence[object]]):
            nonlocal flt, params
            if values:
                if "." not in field:
                    field = f"docs.{field}"
                placeholders = ",".join(["?"] * len(values))
                flt.append(f"{field} IN ({placeholders})")
                params.extend(values)

        add_in("filetype", filters.filetypes)
        add_in("size_bucket", filters.size_buckets)
        add_in("date_bucket", filters.date_buckets)
        add_in("location_id", filters.location_ids)

        filter_sql = " AND ".join(flt) if flt else "1"

        # Build candidate CTE
        ctes: List[str] = []
        cte_params: List[object] = []

        import re
        def like_params(q: str) -> List[str]:
            like = f"%{q.lower()}%"
            return [like, like]

        if q:
            if mode in ("filename", "all"):
                ctes.append(
                    f"SELECT id FROM docs WHERE {filter_sql} AND (LOWER(docs.name) LIKE ? OR LOWER(docs.path) LIKE ?)"
                )
                cte_params.extend(like_params(q))
            if mode in ("content", "all"):
                from .fts import build_match_query
                match = build_match_query(q)
                if match:
                    ctes.append(
                        f"SELECT docs.id FROM content_fts JOIN docs ON docs.id=content_fts.rowid WHERE {filter_sql} AND content_fts MATCH ?"
                    )
                    cte_params.append(match)
        else:
            # No query: candidates are just filtered docs
            ctes.append(f"SELECT id FROM docs WHERE {filter_sql}")

        cte_sql = " UNION " .join(ctes)
        order_sql = (
            "CASE WHEN LOWER(docs.name) LIKE ? THEN 0 ELSE 1 END, docs.mtime_ns DESC"
            if q else "docs.mtime_ns DESC"
        )
        order_params: List[object] = [f"%{q.lower()}%"] if q else []

        sql = (
            "WITH candidate_ids AS (" + cte_sql + ") "
            "SELECT docs.*, locations.path AS location_path "
            "FROM docs JOIN candidate_ids ON candidate_ids.id = docs.id "
            "LEFT JOIN locations ON locations.id = docs.location_id "
            f"ORDER BY {order_sql} LIMIT ?"
        )

        with self._connect() as con:
            con.execute("PRAGMA query_only=1")
            rows = con.execute(sql, (*params, *cte_params, *order_params, limit)).fetchall()

            facets: Dict[str, Dict[str, int]] = {}
            def facet_counts(column: str) -> Dict[str, int]:
                cur = con.execute(
                    f"WITH candidate_ids AS (" + cte_sql + ") "
                    f"SELECT {column}, COUNT(*) FROM docs JOIN candidate_ids ON candidate_ids.id = docs.id GROUP BY {column}",
                    (*params, *cte_params),
                )
                out: Dict[str, int] = {}
                for r in cur.fetchall():
                    key = r[0]
                    key = str(key) if key is not None else ""
                    out[key] = int(r[1])
                return out

            facets["filetype"] = facet_counts("filetype")
            facets["size_bucket"] = facet_counts("size_bucket")
            facets["date_bucket"] = facet_counts("date_bucket")

            # Locations (avoid huge IN lists by joining)
            loc_counts: Dict[str, int] = {}
            cur = con.execute(
                "WITH candidate_ids AS (" + cte_sql + ") "
                "SELECT locations.path, COUNT(*) "
                "FROM docs JOIN candidate_ids ON candidate_ids.id = docs.id "
                "JOIN locations ON locations.id = docs.location_id "
                "GROUP BY locations.path",
                (*params, *cte_params),
            )
            for r in cur.fetchall():
                loc_counts[str(r[0])] = int(r[1])
            facets["location"] = loc_counts

            return rows, facets
