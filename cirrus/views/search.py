from cirrus.delegates import CheckBoxDelegate

from PySide6.QtCore import (
    Qt,
    QModelIndex,
    QItemSelectionModel,
    Signal,
    Slot,
)
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QTreeView,
)


class SearchResultsTreeView(QTreeView):
    checked = Signal()
    unchecked = Signal()
    all_checked = Signal()
    all_unchecked = Signal()

    def __init__(self):
        super().__init__()
        self.shift_down = False
        self.last_checked_index = QModelIndex()
        self.setExpandsOnDoubleClick(False)
        self.setUniformRowHeights(True)
        self.setAnimated(False)
        self.setSortingEnabled(True)
        self.setTextElideMode(Qt.ElideMiddle)
        self.setIndentation(10)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setSelectionMode(QAbstractItemView.NoSelection)
        delegate = CheckBoxDelegate(self)
        self.setItemDelegateForColumn(0, delegate)
        self.clicked.connect(self.toggle_checkbox)

    def setup_header(self):
        # checkbox | name | type | size | last mod
        header = QHeaderView(Qt.Horizontal)
        self.setHeader(header)
        header.setSectionsMovable(True)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSortIndicator(0, Qt.AscendingOrder)
        self.resizeColumnToContents(0)
        self.resizeColumnToContents(1)
        self.resizeColumnToContents(2)
        self.resizeColumnToContents(3)

    @Slot(QKeyEvent)
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Shift:
            self.shift_down = True
        return super().keyPressEvent(event)

    @Slot(QKeyEvent)
    def keyReleaseEvent(self, event):
        self.shift_down = False
        return super().keyReleaseEvent(event)

    @Slot(QModelIndex)
    def toggle_checkbox(self, index):
        if index.isValid() and index.column() == 0:
            indexes = [index]
            if self.shift_down and self.last_checked_index.isValid():
                data = self.last_checked_index.data()
                if index.row() > self.last_checked_index.row():
                    indexes_range = range(
                        self.last_checked_index.row(), index.row()
                    )
                else:
                    indexes_range = range(
                        index.row(), self.last_checked_index.row()
                    )
                for row in indexes_range:
                    indexes.append(self.model().index(row, 0))
            else:
                data = index.data()
            if data == Qt.Checked.value:
                check = Qt.Checked
            else:
                check = Qt.Unchecked
            self.last_checked_index = index
            top = None
            bottom = None
            for index in indexes:
                if index.model().setData(index, check, role=Qt.CheckStateRole):
                    if check == Qt.Checked:
                        self.checked.emit()
                        self.selectionModel().select(
                            index,
                            QItemSelectionModel.Rows |
                            QItemSelectionModel.Select
                        )
                    else:
                        self.unchecked.emit()
                        self.selectionModel().select(
                            index,
                            QItemSelectionModel.Rows |
                            QItemSelectionModel.Deselect
                        )
                    if top is None or top.row() > index.row():
                        top = index
                    if bottom is None or bottom.row() < index.row():
                        bottom = index
            index.model().dataChanged.emit(top, bottom)
            index = index.siblingAtRow(0)
            if check == Qt.Unchecked:
                if not self.model().match(
                    index,
                    Qt.CheckStateRole,
                    Qt.Checked.value,
                    flags=Qt.MatchExactly
                ):
                    self.all_unchecked.emit()
            else:
                if not self.model().match(
                    index,
                    Qt.CheckStateRole,
                    Qt.Unchecked.value,
                    flags=Qt.MatchExactly
                ):
                    self.all_checked.emit()
