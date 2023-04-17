from cirrus.delegates import CheckBoxDelegate

from PySide6.QtCore import Qt, QModelIndex, QItemSelectionModel, Signal, Slot
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QTreeView,
)


class SearchResultsTreeView(QTreeView):
    checked = Signal()
    all_unchecked = Signal()

    def __init__(self):
        super().__init__()
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

    @Slot(QModelIndex)
    def toggle_checkbox(self, index):
        if index.isValid() and index.column() == 0:
            if index.data() == Qt.Checked:
                check = Qt.Unchecked
            else:
                check = Qt.Checked
            if index.model().setData(index, check):
                index.model().dataChanged.emit(index, index)
                if check == Qt.Checked:
                    self.checked.emit()
                    self.selectionModel().select(
                        index,
                        QItemSelectionModel.Rows | QItemSelectionModel.Select
                    )
                else:
                    self.selectionModel().select(
                        index,
                        QItemSelectionModel.Rows | QItemSelectionModel.Deselect
                    )
                    index = index.siblingAtRow(0)
                    if not self.model().match(
                        index,
                        Qt.DisplayRole,
                        Qt.Checked,
                        flags=Qt.MatchExactly
                    ):
                        self.all_unchecked.emit()
