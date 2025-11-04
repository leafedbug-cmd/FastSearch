from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, List, Sequence, Set

from watchdog.events import FileSystemEventHandler, FileSystemEvent
from watchdog.observers import Observer

from fastsearch.index.docs_repo import DocsRepo
from .indexer import ContentIndexer


log = logging.getLogger(__name__)


DEFAULT_EXCLUDES = {".git", "node_modules", "venv", ".venv", "__pycache__", ".idea", ".vscode"}


@dataclass
class WatcherConfig:
    roots: Sequence[Path]
    exclude_dir_names: Set[str]
    skip_initial_if_index_present: bool = True


class _Handler(FileSystemEventHandler):
    def __init__(self, repo: DocsRepo, roots: Sequence[Path], indexer: ContentIndexer | None) -> None:
        super().__init__()
        self.repo = repo
        self.roots = roots
        self.indexer = indexer

    def on_created(self, event: FileSystemEvent):  # type: ignore[override]
        if event.is_directory:
            return
        p = Path(event.src_path)
        self.repo.upsert_file(p, self.roots)
        if self.indexer:
            self.indexer.enqueue(p)

    def on_modified(self, event: FileSystemEvent):  # type: ignore[override]
        if event.is_directory:
            return
        p = Path(event.src_path)
        self.repo.upsert_file(p, self.roots)
        if self.indexer:
            self.indexer.enqueue(p)

    def on_moved(self, event):  # type: ignore[override]
        if getattr(event, "dest_path", None):
            p = Path(event.dest_path)
            self.repo.upsert_file(p, self.roots)
            if self.indexer:
                self.indexer.enqueue(p)
        self.repo.mark_deleted(Path(event.src_path))

    def on_deleted(self, event: FileSystemEvent):  # type: ignore[override]
        if event.is_directory:
            return
        self.repo.mark_deleted(Path(event.src_path))


class WatchService:
    def __init__(self, repo: DocsRepo, cfg: WatcherConfig, indexer: ContentIndexer | None = None) -> None:
        self.repo = repo
        self.cfg = cfg
        self.indexer = indexer
        self._observers: List[Observer] = []
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._on_status: Callable[[str], None] | None = None

    def on_status(self, fn: Callable[[str], None]) -> None:
        self._on_status = fn

    def _emit_status(self, msg: str) -> None:
        log.info(msg)
        if self._on_status:
            self._on_status(msg)

    def _scan_root(self, root: Path) -> None:
        scanned = 0
        self._emit_status(f"Indexing {root}…")
        # ensure progress entry exists
        self.repo.update_location_scan_state(str(root), complete=False, last_scan_count=0)
        for dirpath, dirnames, filenames in os_walk_filtered(root, self.cfg.exclude_dir_names):
            for fn in filenames:
                p = Path(dirpath) / fn
                self.repo.upsert_file(p, self.cfg.roots)
                if self.indexer:
                    self.indexer.enqueue(p)
                scanned += 1
                if scanned % 500 == 0:
                    self.repo.update_location_scan_state(str(root), last_scan_count=scanned)
                    self._emit_status(f"Indexing {root}… {scanned} files")
                if self._stop_event.is_set():
                    return
        self.repo.update_location_scan_state(str(root), complete=True, last_scan_count=scanned)
        self._emit_status(f"Indexing complete for {root} ({scanned} files)")

    def start(self) -> None:
        # Possibly skip scanning completed roots; resume incomplete ones
        to_scan: List[Path] = []
        for root in self.cfg.roots:
            complete = self.repo.is_initial_scan_complete(str(root)) if self.cfg.skip_initial_if_index_present else False
            if not complete:
                to_scan.append(root)
        if not to_scan and self.cfg.skip_initial_if_index_present:
            existing = self.repo.count_docs_for_location_paths([str(p) for p in self.cfg.roots])
            self._emit_status(f"Loaded index ({existing} files)")
        else:
            for root in to_scan:
                if self._stop_event.is_set():
                    break
                self._scan_root(root)

        # Enqueue any docs missing content for background indexing
        try:
            if self.indexer:
                missing = self.repo.iter_paths_missing_content(self.cfg.roots, batch=5000)
                for p in missing:
                    self.indexer.enqueue(p)
                if missing:
                    self._emit_status(f"Queueing content index for {len(missing)} files…")
        except Exception:
            pass

        # Start observers
        handler = _Handler(self.repo, self.cfg.roots, self.indexer)
        for root in self.cfg.roots:
            ob = Observer()
            ob.schedule(handler, str(root), recursive=True)
            ob.daemon = True
            ob.start()
            self._observers.append(ob)
        self._emit_status("Watching for changes…")

        # Wait loop
        while not self._stop_event.is_set():
            time.sleep(0.5)

    def start_in_thread(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self.start, name="WatchService", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        for ob in self._observers:
            try:
                ob.stop()
                ob.join(timeout=2.0)
            except Exception:
                pass


def os_walk_filtered(root: Path, exclude_dir_names: Set[str]):
    # A generator similar to os.walk but filters excluded dirnames in-place
    from os import walk
    for dirpath, dirnames, filenames in walk(root):
        # Filter exclude dirs by name (case-insensitive)
        dirnames[:] = [d for d in dirnames if d.lower() not in exclude_dir_names]
        yield dirpath, dirnames, filenames
