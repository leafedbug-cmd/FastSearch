from __future__ import annotations

from typing import Dict, List, Tuple

from PySide6 import QtCore, QtWidgets

from ..models.facets_model import FacetCounts, FacetSelection


class _FacetGroup(QtWidgets.QGroupBox):
    selectionChanged = QtCore.Signal()

    def __init__(self, title: str) -> None:
        super().__init__(title)
        self.setLayout(QtWidgets.QVBoxLayout())
        self._checks: Dict[str, QtWidgets.QCheckBox] = {}

    def set_items(self, items: Dict[str, int], selected: List[str]) -> None:
        # Clear
        layout = self.layout()
        while layout.count():
            w = layout.takeAt(0).widget()
            if w:
                w.deleteLater()
        self._checks.clear()
        # Add sorted by name
        for key, count in sorted(items.items(), key=lambda kv: kv[0].lower()):
            label = f"{key} ({count})" if key else f"(Unknown) ({count})"
            cb = QtWidgets.QCheckBox(label)
            cb.setProperty("facet_key", key)
            cb.setChecked(key in selected)
            cb.stateChanged.connect(self.selectionChanged.emit)
            layout.addWidget(cb)
            self._checks[key] = cb
        layout.addStretch(1)

    def selected(self) -> List[str]:
        return [k for k, cb in self._checks.items() if cb.isChecked()]


class FacetsPanel(QtWidgets.QScrollArea):
    filtersChanged = QtCore.Signal(FacetSelection)

    def __init__(self) -> None:
        super().__init__()
        self.setWidgetResizable(True)
        self._inner = QtWidgets.QWidget()
        self.setWidget(self._inner)
        self._layout = QtWidgets.QVBoxLayout(self._inner)

        self.group_type = _FacetGroup("File Type")
        self.group_size = _FacetGroup("Size")
        self.group_date = _FacetGroup("Date Modified")
        self.group_location = _FacetGroup("Location")

        for g in (self.group_type, self.group_size, self.group_date, self.group_location):
            g.selectionChanged.connect(self._emit)
            self._layout.addWidget(g)

        self._layout.addStretch(1)

    def update_counts(self, counts: FacetCounts, selection: FacetSelection) -> None:
        self.group_type.set_items(counts.filetype, selection.filetype)
        self.group_size.set_items(counts.size_bucket, selection.size_bucket)
        self.group_date.set_items(counts.date_bucket, selection.date_bucket)
        self.group_location.set_items(counts.location, selection.location)

    def _emit(self) -> None:
        sel = FacetSelection(
            filetype=self.group_type.selected(),
            size_bucket=self.group_size.selected(),
            date_bucket=self.group_date.selected(),
            location=self.group_location.selected(),
        )
        self.filtersChanged.emit(sel)

