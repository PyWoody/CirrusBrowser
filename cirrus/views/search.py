from cirrus.delegates import CheckBoxDelegate

from PySide6.QtCore import Qt, QModelIndex, Slot
from PySide6.QtGui import QStandardItem
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QTreeView,
)


class SearchResultsTreeView(QTreeView):

    def __init__(self):
        super().__init__()
        self.setExpandsOnDoubleClick(False)
        self.setUniformRowHeights(True)
        self.setAnimated(False)
        self.setSortingEnabled(True)
        self.setTextElideMode(Qt.ElideMiddle)
        self.setIndentation(10)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        # self.setSelectionBehavior(QAbstractItemView.SelectRows)
        # self.setSelectionMode(QAbstractItemView.ExtendedSelection)
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
            check = 1 if index.data() == 0 else 0
            if index.model().setData(index, Qt.Checked):
                index.model().dataChanged.emit(index, index)
