from cirrus.models import ListModel

from PySide6.QtCore import QEvent, Qt, Signal, Slot, QModelIndex
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QLineEdit,
    QListView,
    QToolButton,
)


class NavBarLineEdit(QLineEdit):
    selection_made = Signal(str)

    def __init__(self, parent):
        super().__init__(parent)
        self.view = NavBarListView(parent)
        self.view.selection_made.connect(self.selection_made.emit)
        self.returnPressed.connect(self.clear_focus)

    def set_model(self, items):
        cleaned_items = []
        for item in items:
            if item not in cleaned_items:
                cleaned_items.append(item)
        model = ListModel(cleaned_items)
        prev_model = self.view.model()
        prev_selection_model = self.view.selectionModel()
        self.view.setModel(model)
        if prev_model:
            prev_model.deleteLater()
        if prev_selection_model:
            prev_selection_model.deleteLater()

    @Slot()
    def clear_focus(self):
        self.clearFocus()
        self.view.hide()

    def focusInEvent(self, event):
        if (row_count := self.view.model().rowCount()) > 0:
            self.view.show()
            height = row_count * self.view.sizeHintForRow(0)
            frame = self.frameGeometry()
            self.view.setGeometry(
                frame.x() - 10,
                self.view.y(),
                frame.width(),
                height + 5,
            )
        return super().focusInEvent(event)

    def focusOutEvent(self, event):
        self.clear_focus()
        return super().focusOutEvent(event)


class NavBarListView(QListView):
    selection_made = Signal(str)

    def __init__(self, parent):
        super().__init__(parent)
        self.hide()
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setUniformItemSizes(True)
        self.setTextElideMode(Qt.ElideMiddle)
        self.setDragDropMode(QAbstractItemView.NoDragDrop)
        self.setMouseTracking(True)
        self.clicked.connect(self.location_clicked)
        self.entered.connect(self.on_hover)

    @Slot(QModelIndex)
    def location_clicked(self, index):
        if data := index.data():
            self.selection_made.emit(data)

    @Slot(QModelIndex)
    def on_hover(self, index):
        if not index.isValid():
            return
        self.setCurrentIndex(index)
