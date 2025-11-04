from __future__ import annotations

from PySide6 import QtGui


# Vibrant color palette per file type
FILETYPE_COLORS: dict[str, str] = {
    "PDF": "#ff5a54",           # red
    "Document": "#5aa6ff",      # blue
    "Spreadsheet": "#2bd57b",   # green
    "Presentation": "#ff8a1c",  # orange
    "Image": "#c35aff",         # purple
    "Code": "#00d3d3",          # teal
    "Archive": "#f2c12e",       # yellow
    "Other": "#9aa0a6",         # gray
}


def color_for_filetype(ft: str) -> QtGui.QColor:
    hex_color = FILETYPE_COLORS.get(ft, FILETYPE_COLORS["Other"])
    return QtGui.QColor(hex_color)


def tinted_background(ft: str, alpha: int = 28) -> QtGui.QBrush:
    c = color_for_filetype(ft)
    c = QtGui.QColor(c)  # copy
    c.setAlpha(max(0, min(255, alpha)))
    return QtGui.QBrush(c)

