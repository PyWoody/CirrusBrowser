from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QItemDelegate,
    QStyle,
    QStyledItemDelegate,
    QStyleOptionProgressBar,
)


class CheckBoxDelegate(QItemDelegate):

    def __init_(self, parent=None):
        super().__init__(parent)

    def paint(self, painter, option, index):
        if index.data() == Qt.Checked:
            status = Qt.Checked
        else:
            status = Qt.Unchecked
        self.drawCheck(painter, option, option.rect, status)
        self.drawFocus(painter, option, option.rect)


class ProgressBarDelegate(QStyledItemDelegate):

    def __init__(self, parent=None):
        super().__init__(parent)

    def paint(self, painter, option, index):
        progress = index.data()
        if not progress:
            return
        pbar = QStyleOptionProgressBar()
        pbar.rect = option.rect
        pbar.minimum = 0
        pbar.maximum = 100
        pbar.progress = progress
        if progress == 100:
            pbar.text = '100%'
        else:
            pbar.text = f'{progress:.1f}%'
        pbar.textVisible = True
        pbar.state |= QStyle.StateFlag.State_Horizontal
        if option.widget is not None:
            style = option.widget.style()
        else:
            style = QApplication.style()
        style.drawControl(
            QStyle.ControlElement.CE_ProgressBar, pbar, painter, option.widget
        )
