from __future__ import annotations

import os
from pathlib import Path

from PySide6 import QtCore, QtGui, QtWidgets


class PreviewPane(QtWidgets.QWidget):
    def __init__(self, preview_max_bytes: int = 2_000_000) -> None:
        super().__init__()
        self.preview_max_bytes = preview_max_bytes
        layout = QtWidgets.QVBoxLayout(self)

        self.title = QtWidgets.QLabel("Preview")
        self.title.setStyleSheet("font-weight: bold; font-size: 12pt;")
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
            details = f"{p}\nSize: {st.st_size:,} bytes\nModified: {QtCore.QDateTime.fromSecsSinceEpoch(int(st.st_mtime)).toString()}"
            self.info.setText(details)
        except Exception as e:
            self.info.setText(str(p))

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
        self.text.setPlainText("(No preview available)")

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

