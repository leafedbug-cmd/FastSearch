from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import List, Sequence

from PySide6 import QtCore, QtWidgets

from fastsearch.index.db import initialize
from fastsearch.index.docs_repo import DocsRepo
from fastsearch.service.watcher import WatchService, WatcherConfig, DEFAULT_EXCLUDES
from .views.main_window import MainWindow


log = logging.getLogger(__name__)


def _load_default_watch_dirs() -> List[Path]:
    # Try to infer a sensible default: user's Documents folder
    home = Path.home()
    candidates = []
    for name in ("Documents", "downloads", "Desktop", "documents"):
        p = home / name
        if p.exists() and p.is_dir():
            candidates.append(p)
    # Fallback to home
    if not candidates:
        candidates.append(home)
    return candidates


def run_gui() -> None:
    # Basic logging
    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")

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
    watch_dirs = _load_default_watch_dirs()
    watcher = WatchService(repo, WatcherConfig(roots=watch_dirs, exclude_dir_names={s.lower() for s in DEFAULT_EXCLUDES}))

    win = MainWindow(repo=repo, watch_dirs=watch_dirs, watcher=watcher)
    win.resize(1250, 760)
    win.show()

    watcher.start_in_thread()

    app.exec()

