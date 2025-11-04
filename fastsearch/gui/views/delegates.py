from __future__ import annotations

from PySide6 import QtCore, QtGui, QtWidgets

from ..style.colors import color_for_filetype


class PillDelegate(QtWidgets.QStyledItemDelegate):
    """Paints a rounded color pill in the cell with the text centered."""

    def paint(self, painter: QtGui.QPainter, option: QtWidgets.QStyleOptionViewItem, index: QtCore.QModelIndex) -> None:  # type: ignore[override]
        text = str(index.data(QtCore.Qt.DisplayRole) or "")
        ft = index.data(QtCore.Qt.UserRole + 1) or text
        color = color_for_filetype(ft)
        # Base style painting (for selection highlighting background)
        opt = QtWidgets.QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)
        style = opt.widget.style() if opt.widget else QtWidgets.QApplication.style()
        style.drawPrimitive(QtWidgets.QStyle.PE_PanelItemViewItem, opt, painter, opt.widget)

        if not text:
            return

        # Draw pill
        r = opt.rect.adjusted(8, 4, -8, -4)
        path = QtGui.QPainterPath()
        radius = r.height() / 2
        path.addRoundedRect(r, radius, radius)

        painter.save()
        painter.setRenderHint(QtGui.QPainter.Antialiasing, True)
        painter.fillPath(path, color)

        # Text
        pen = QtGui.QPen(QtGui.QColor("#ffffff"))
        painter.setPen(pen)
        font = painter.font()
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(r, QtCore.Qt.AlignCenter, text)
        painter.restore()

    def sizeHint(self, option: QtWidgets.QStyleOptionViewItem, index: QtCore.QModelIndex) -> QtCore.QSize:  # type: ignore[override]
        base = super().sizeHint(option, index)
        return QtCore.QSize(base.width(), max(base.height(), 28))
