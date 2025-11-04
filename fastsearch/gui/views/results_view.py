from __future__ import annotations

from pathlib import Path
from typing import List

from PySide6 import QtCore, QtGui, QtWidgets

from ..models.results_model import ResultsTableModel


class ResultsView(QtWidgets.QTableView):
    pathActivated = QtCore.Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.setModel(ResultsTableModel())
        self.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        self.setAlternatingRowColors(True)
        self.setShowGrid(False)
        self.setSortingEnabled(False)
        self.verticalHeader().hide()
        self.horizontalHeader().setStretchLastSection(True)
        self.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
        self.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        self.horizontalHeader().setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        self.horizontalHeader().setSectionResizeMode(3, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        self.horizontalHeader().setSectionResizeMode(4, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        self.doubleClicked.connect(self._on_double_clicked)

    def set_rows(self, rows: List[dict]) -> None:
        model: ResultsTableModel = self.model()  # type: ignore[assignment]
        model.set_rows(rows)
        if rows:
            self.selectRow(0)

    def current_path(self) -> str | None:
        idxs = self.selectionModel().selectedRows()
        if not idxs:
            return None
        row = idxs[0].row()
        model: ResultsTableModel = self.model()  # type: ignore[assignment]
        return model.row_path(row)

    def _on_double_clicked(self, index: QtCore.QModelIndex) -> None:
        model: ResultsTableModel = self.model()  # type: ignore[assignment]
        path = model.row_path(index.row())
        self.pathActivated.emit(path)

