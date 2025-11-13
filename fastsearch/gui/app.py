from __future__ import annotations

import logging
import os
import os as _os
from pathlib import Path
from typing import List

from PySide6 import QtWidgets

from fastsearch.index.db import initialize
from fastsearch.index.docs_repo import DocsRepo
from fastsearch.service.watcher import WatchService, WatcherConfig, DEFAULT_EXCLUDES
from fastsearch.service.indexer import ContentIndexer
from fastsearch.config.settings import (
    Settings,
    default_watch_dirs,
    resolved_watch_dirs_from_settings,
)
from .views.main_window import MainWindow


log = logging.getLogger(__name__)


def _load_env_watch_dirs() -> List[Path]:
    env = os.environ.get("FASTSEARCH_WATCH_DIRS")
    if not env:
        return []
    parts = [p.strip() for p in env.split(os.pathsep) if p.strip()]
    paths: List[Path] = []
    for p in parts:
        pp = Path(p)
        if pp.exists() and pp.is_dir():
            paths.append(pp)
    return paths


def _fallback_watch_dirs() -> List[Path]:
    try:
        if os.name == "nt":
            system_drive = os.environ.get("SystemDrive", "C:")
            root = Path(system_drive + "\\")
            if root.exists():
                return [root]
    except Exception:
        pass
    home = Path.home()
    candidates = []
    for name in ("Documents", "Downloads", "Desktop"):
        p = home / name
        if p.exists() and p.is_dir():
            candidates.append(p)
    if not candidates:
        candidates.append(home)
    return candidates


def _resolve_watch_dirs(settings: Settings) -> List[Path]:
    env = _load_env_watch_dirs()
    if env:
        return env

    saved = resolved_watch_dirs_from_settings(settings)
    if saved:
        return saved

    defaults = default_watch_dirs()
    if defaults:
        return defaults

    return _fallback_watch_dirs()


def run_gui() -> None:
    # Basic logging
    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
    logging.getLogger("pypdf").setLevel(logging.ERROR)

    # Ensure DB initialized
    initialize()

    app = QtWidgets.QApplication([])
    app.setOrganizationName("FastSearch")
    app.setApplicationName("FastSearch")

    # Apply dark-ish stylesheet
    qss_path = Path(__file__).parent / "assets" / "qss" / "dark.qss"
    if qss_path.exists():
        with open(qss_path, "r", encoding="utf-8") as f:
            app.setStyleSheet(f.read())

    repo = DocsRepo()
    settings = Settings.load()
    watch_dirs = _resolve_watch_dirs(settings)
    # Speed: run content indexer with CPU-1 workers (at least 1)
    _cpu = _os.cpu_count() or 2
    _env_workers = _os.environ.get("FASTSEARCH_INDEXER_WORKERS")
    if _env_workers and _env_workers.isdigit():
        _workers = max(1, int(_env_workers))
    else:
        _workers = max(1, min(4, _cpu - 1))
    indexer = ContentIndexer(workers=_workers, settings=settings, roots=watch_dirs)
    log.info(f"Content indexer using {_workers} workers")
    indexer.start()
    watcher = WatchService(repo, WatcherConfig(roots=watch_dirs, exclude_dir_names={s.lower() for s in DEFAULT_EXCLUDES}), indexer=indexer)

    win = MainWindow(repo=repo, watch_dirs=watch_dirs, watcher=watcher, settings=settings)
    win.resize(1250, 760)
    win.show()

    watcher.start_in_thread()

    app.exec()


if __name__ == "__main__":
    run_gui()
