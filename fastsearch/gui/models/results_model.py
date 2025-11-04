from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import List, Sequence

from PySide6 import QtCore, QtGui, QtWidgets
from ..style.colors import tinted_background


class ResultsTableModel(QtCore.QAbstractTableModel):
    HEADERS = ["Name", "Location", "Type", "Size", "Modified"]

    def __init__(self, rows: List[dict] | None = None) -> None:
        super().__init__()
        self._rows: List[dict] = rows or []

    def set_rows(self, rows: List[dict]) -> None:
        self.beginResetModel()
        self._rows = rows
        self.endResetModel()

    def rowCount(self, parent: QtCore.QModelIndex = QtCore.QModelIndex()) -> int:  # type: ignore[override]
        if parent.isValid():
            return 0
        return len(self._rows)

    def columnCount(self, parent: QtCore.QModelIndex = QtCore.QModelIndex()) -> int:  # type: ignore[override]
        return len(self.HEADERS)

    def data(self, index: QtCore.QModelIndex, role: int = QtCore.Qt.DisplayRole):  # type: ignore[override]
        if not index.isValid():
            return None
        row = self._rows[index.row()]
        col = index.column()
        if role == QtCore.Qt.DisplayRole:
            if col == 0:
                return row.get("name")
            if col == 1:
                return row.get("location_path", "")
            if col == 2:
                return row.get("filetype")
            if col == 3:
                return self._format_size(row.get("size_bytes", 0))
            if col == 4:
                ts = row.get("mtime_ns", 0) / 1e9
                return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")
        if role == QtCore.Qt.BackgroundRole:
            ft = (row.get("filetype") or "")
            return tinted_background(ft, alpha=24)
        if role == QtCore.Qt.DecorationRole:
            if col == 0:
                # Choose icon by filetype (simple mapping)
                ft = (row.get("filetype") or "").lower()
                return self._icon_for_type(ft)
        if role == QtCore.Qt.ToolTipRole:
            return row.get("path")
        return None

    def headerData(self, section: int, orientation: QtCore.Qt.Orientation, role: int = QtCore.Qt.DisplayRole):  # type: ignore[override]
        if orientation == QtCore.Qt.Horizontal and role == QtCore.Qt.DisplayRole:
            return self.HEADERS[section]
        return None

    def row_path(self, row: int) -> str:
        return self._rows[row].get("path", "")

    @staticmethod
    def _format_size(size: int) -> str:
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size < 1024.0:
                return f"{size:.0f} {unit}"
            size /= 1024.0
        return f"{size:.0f} PB"

    @staticmethod
    def _icon_for_type(ft: str):
        # Simple icon mapping using standard icons
        style = QtWidgets.QApplication.style()
        if "image" in ft:
            return style.standardIcon(QtWidgets.QStyle.SP_FileIcon)
        if "pdf" in ft:
            return style.standardIcon(QtWidgets.QStyle.SP_FileIcon)
        if "code" in ft:
            return style.standardIcon(QtWidgets.QStyle.SP_FileIcon)
        if "spreadsheet" in ft:
            return style.standardIcon(QtWidgets.QStyle.SP_FileIcon)
        if "presentation" in ft:
            return style.standardIcon(QtWidgets.QStyle.SP_FileIcon)
        if "archive" in ft:
            return style.standardIcon(QtWidgets.QStyle.SP_DirIcon)
        return style.standardIcon(QtWidgets.QStyle.SP_FileIcon)
