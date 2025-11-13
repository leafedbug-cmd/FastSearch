from __future__ import annotations

import os
from pathlib import Path

from PySide6 import QtCore, QtGui, QtWidgets
from fastsearch.index.docs_repo import classify_filetype
from fastsearch.config.settings import Settings
from ..style.colors import color_for_filetype


class PreviewPane(QtWidgets.QWidget):
    def __init__(self, preview_max_bytes: int = 2_000_000, settings: Settings | None = None) -> None:
        super().__init__()
        self.preview_max_bytes = preview_max_bytes
        self.settings = settings or Settings()
        layout = QtWidgets.QVBoxLayout(self)

        self.title = QtWidgets.QLabel("Preview")
        self.title.setStyleSheet("font-weight: bold; font-size: 12pt; padding:8px; border-radius:6px; background:#2a2c31;")
        layout.addWidget(self.title)

        self.info = QtWidgets.QLabel("")
        self.info.setWordWrap(True)
        layout.addWidget(self.info)

        self.text = QtWidgets.QPlainTextEdit()
        self.text.setReadOnly(True)
        layout.addWidget(self.text, 1)

        btn_row = QtWidgets.QHBoxLayout()
        layout.addLayout(btn_row)
        self.btn_open = QtWidgets.QPushButton("Open")
        self.btn_reveal = QtWidgets.QPushButton("Show in Folder")
        btn_row.addWidget(self.btn_open)
        btn_row.addWidget(self.btn_reveal)
        btn_row.addStretch(1)

        self.btn_open.clicked.connect(self._open)
        self.btn_reveal.clicked.connect(self._reveal)

        self._path: str | None = None

    def set_path(self, path: str | None) -> None:
        self._path = path
        if not path:
            self.title.setText("Preview")
            self.info.setText("")
            self.text.setPlainText("")
            return
        p = Path(path)
        self.title.setText(p.name)
        try:
            st = p.stat()
            ft = classify_filetype(p.suffix)
            ext = p.suffix.lstrip('.').upper()
            details = (
                f"{p}\nType: {ext} {ft}\n"
                f"Size: {st.st_size:,} bytes\n"
                f"Modified: {QtCore.QDateTime.fromSecsSinceEpoch(int(st.st_mtime)).toString()}"
            )
            self.info.setText(details)
        except Exception as e:
            self.info.setText(str(p))

        # Color accent by file type
        ft = classify_filetype(p.suffix)
        c = color_for_filetype(ft)
        text_color = "#ffffff"
        self.title.setStyleSheet(f"font-weight:bold; font-size:12pt; padding:8px; border-radius:6px; background:{c.name()}; color:{text_color};")

        # Try to preview text files (small)
        if p.suffix.lower() in (".txt", ".md", ".py", ".json", ".log", ".csv", ".yaml", ".yml"):
            try:
                if p.stat().st_size <= self.preview_max_bytes:
                    with open(p, "r", encoding="utf-8", errors="replace") as f:
                        head = f.read(64_000)
                        self.text.setPlainText(head)
                        return
            except Exception:
                pass
        # If OCR enabled and image file, attempt OCR in background
        if self.settings.enable_ocr and p.suffix.lower() in (".png", ".jpg", ".jpeg", ".bmp", ".tiff"):
            self.text.setPlainText("Running OCR…")
            self._run_ocr(p)
            return
        self.text.setPlainText("(No preview available)")

    def _run_ocr(self, path: Path) -> None:
        def work() -> str:
            try:
                try:
                    import pytesseract  # type: ignore
                except Exception:
                    return "OCR unavailable: install pytesseract and Tesseract OCR."
                try:
                    from PIL import Image  # type: ignore
                except Exception:
                    return "OCR unavailable: install Pillow."
                with Image.open(path) as img:
                    text = pytesseract.image_to_string(img)
                return text.strip() or "(No text detected)"
            except Exception as e:
                return f"OCR failed: {e}"

        import threading
        target_path = str(path)

        def done(result: str) -> None:
            def apply() -> None:
                if self._path == target_path:
                    self.text.setPlainText(result)
            QtCore.QTimer.singleShot(0, apply)

        threading.Thread(target=lambda: done(work()), daemon=True).start()

    def _open(self) -> None:
        if not self._path:
            return
        QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(self._path))

    def _reveal(self) -> None:
        if not self._path:
            return
        p = Path(self._path)
        folder = str(p.parent)
        QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(folder))
