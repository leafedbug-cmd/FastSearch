from __future__ import annotations

import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from PySide6 import QtCore, QtGui, QtWidgets

from fastsearch.index.docs_repo import DocsRepo, SearchFilters
from .results_view import ResultsView
from .facets_panel import FacetsPanel
from .preview_pane import PreviewPane
from ..models.facets_model import FacetCounts, FacetSelection
from .delegates import PillDelegate
from fastsearch.config.settings import Settings


@dataclass
class SearchState:
    text: str = ""
    facets: FacetSelection = field(default_factory=FacetSelection)


class SearchWorker(QtCore.QObject):
    resultsReady = QtCore.Signal(list, dict)  # rows, facets

    def __init__(self, repo: DocsRepo) -> None:
        super().__init__()
        self.repo = repo
        self._lock = threading.Lock()
        self._latest_seq = 0

    @QtCore.Slot(int, str, str, object)
    def run_search(self, seq: int, text: str, mode: str, sel_obj: object) -> None:
        sel: FacetSelection = sel_obj  # type: ignore[assignment]
        with self._lock:
            self._latest_seq = max(self._latest_seq, seq)
            current = self._latest_seq
        loc_ids = self.repo.location_ids_for_paths(sel.location)
        filters = SearchFilters(
            filetypes=sel.filetype or None,
            size_buckets=sel.size_bucket or None,
            date_buckets=sel.date_bucket or None,
            location_ids=loc_ids or None,
        )
        # Map selected locations (paths) → ids
        # We’ll resolve via a quick lookup using the repo’s connection in search()
        rows, facets = self.repo.search(text, filters, mode=mode)

        # Replace location facet keys with readable paths (already done by repo)
        # Note: rows need location path for table; fetch via join in repo
        # Provide rows as dicts with location_path key
        out_rows = []
        for r in rows:
            d = dict(r)
            d.setdefault("location_path", "")
            out_rows.append(d)
        if seq == current:
            self.resultsReady.emit(out_rows, facets)


class MainWindow(QtWidgets.QMainWindow):
    searchRequested = QtCore.Signal(int, str, str, object)

    def __init__(self, repo: DocsRepo, watch_dirs: List[Path], watcher, settings: Settings | None = None) -> None:
        super().__init__()
        self.setWindowTitle("FastSearch")
        self.repo = repo
        self.watch_dirs = watch_dirs
        self.watcher = watcher
        self.settings = settings or Settings()

        self._seq = 0
        self._state = SearchState()

        # Toolbar: search field + actions
        toolbar = QtWidgets.QToolBar()
        toolbar.setMovable(False)
        self.addToolBar(toolbar)
        self.search_edit = QtWidgets.QLineEdit()
        self.search_edit.setPlaceholderText("Search files… (name or path)")
        self.search_edit.textChanged.connect(self._schedule_search)
        toolbar.addWidget(self.search_edit)
        toolbar.addSeparator()
        self.settings_btn = QtWidgets.QToolButton()
        self.settings_btn.setText("Settings")
        self.settings_btn.clicked.connect(self._show_settings)
        toolbar.addWidget(self.settings_btn)

        # Central layout: left facets, center results, right preview
        splitter = QtWidgets.QSplitter()
        self.setCentralWidget(splitter)

        self.facets_panel = FacetsPanel()
        splitter.addWidget(self.facets_panel)

        center = QtWidgets.QWidget()
        center_layout = QtWidgets.QVBoxLayout(center)
        self.results = ResultsView()
        center_layout.addWidget(self.results)
        # Color pill delegate for Type column
        self.results.setItemDelegateForColumn(2, PillDelegate(self.results))
        splitter.addWidget(center)

        self.preview = PreviewPane(settings=self.settings)
        splitter.addWidget(self.preview)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setStretchFactor(2, 0)

        # Status bar
        self.status = self.statusBar()
        self._status_label = QtWidgets.QLabel("Ready")
        self.status.addPermanentWidget(self._status_label)

        # Connections
        self.facets_panel.filtersChanged.connect(self._on_facets_changed)
        self.results.selectionModel().selectionChanged.connect(self._on_selection_changed)
        self.results.pathActivated.connect(self._open_path)
        # Route watcher status via queued signal to the UI thread
        self.watcher.on_status(lambda msg: self.statusMessage.emit(msg))

        # Search worker thread
        self._thread = QtCore.QThread(self)
        self._worker = SearchWorker(self.repo)
        self._worker.moveToThread(self._thread)
        self._thread.start()
        self._worker.resultsReady.connect(self._apply_results)
        # Connect signal to worker (queued across threads)
        self.searchRequested.connect(self._worker.run_search)
        # Status messages from background threads
        self.statusMessage.connect(self._set_status)

        # Debounce timer
        self._timer = QtCore.QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(200)
        self._timer.timeout.connect(self._do_search)

        # Initial search
        QtCore.QTimer.singleShot(300, self._do_search)

    def _set_status(self, text: str) -> None:
        self._status_label.setText(text)

    def _schedule_search(self) -> None:
        self._timer.start()

    def _do_search(self) -> None:
        self._seq += 1
        text = self.search_edit.text()
        sel = self._state.facets
        # Dispatch to worker via signal
        self.searchRequested.emit(self._seq, text, 'all', sel)

    @QtCore.Slot(list, dict)
    def _apply_results(self, rows: List[dict], facets: Dict[str, Dict[str, int]]) -> None:
        self.results.set_rows(rows)
        counts = FacetCounts(
            filetype=facets.get("filetype", {}),
            size_bucket=facets.get("size_bucket", {}),
            date_bucket=facets.get("date_bucket", {}),
            location=facets.get("location", {}),
        )
        self.facets_panel.update_counts(counts, self._state.facets)
        self._status_label.setText(f"{len(rows)} results")

    def _on_facets_changed(self, sel: FacetSelection) -> None:
        self._state.facets = sel
        self._schedule_search()

    def _on_selection_changed(self) -> None:
        path = self.results.current_path()
        self.preview.set_path(path)

    def _open_path(self, path: str) -> None:
        QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(path))

    def _show_settings(self) -> None:
        # Simple dialog showing the current watch dirs
        dlg = QtWidgets.QDialog(self)
        dlg.setWindowTitle("Settings")
        layout = QtWidgets.QVBoxLayout(dlg)
        layout.addWidget(QtWidgets.QLabel("Watched Folders:"))
        listw = QtWidgets.QListWidget()
        for p in self.watch_dirs:
            listw.addItem(str(p))
        layout.addWidget(listw)
        btn_row = QtWidgets.QHBoxLayout()
        add_btn = QtWidgets.QPushButton("Add Folder…")
        rem_btn = QtWidgets.QPushButton("Remove")
        btn_row.addWidget(add_btn)
        btn_row.addWidget(rem_btn)
        btn_row.addStretch(1)
        layout.addLayout(btn_row)

        # OCR toggle
        ocr_cb = QtWidgets.QCheckBox("Enable OCR for images (Preview)")
        ocr_cb.setChecked(self.settings.enable_ocr)
        layout.addWidget(ocr_cb)

        close_btn = QtWidgets.QPushButton("Close")
        close_btn.clicked.connect(dlg.accept)
        layout.addWidget(close_btn)

        def add_folder():
            path = QtWidgets.QFileDialog.getExistingDirectory(self, "Choose folder to watch")
            if path:
                self.watch_dirs.append(Path(path))
                listw.addItem(path)

        def remove_selected():
            for it in listw.selectedItems():
                p = Path(it.text())
                if p in self.watch_dirs:
                    self.watch_dirs.remove(p)
                listw.takeItem(listw.row(it))

        add_btn.clicked.connect(add_folder)
        rem_btn.clicked.connect(remove_selected)
        if dlg.exec():
            self.settings.enable_ocr = ocr_cb.isChecked()
            try:
                self.settings.save()
            except Exception:
                pass

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:  # type: ignore[override]
        try:
            if self.watcher:
                self.watcher.stop()
        except Exception:
            pass
        try:
            self._thread.quit()
            self._thread.wait(2000)
        except Exception:
            pass
        super().closeEvent(event)


