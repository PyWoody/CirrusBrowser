import heapq

from cirrus.delegates import ProgressBarDelegate

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QAbstractItemView, QHeaderView, QTreeView


# NOTE: `setSectionResizeMode` causes seg faults. No idea why


class ErrorsDatabaseTreeView(QTreeView):

    def __init__(self, *, parent=None):
        super().__init__(parent)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setSortingEnabled(True)

    def setup_header(self):
        header = QHeaderView(Qt.Horizontal)
        self.setHeader(header)
        # Since there are no custom columns, these stay true to the DB
        header.setSectionHidden(0, True)
        header.setSectionHidden(4, True)
        header.setSectionHidden(5, True)
        # header.setSectionResizeMode(8, QHeaderView.Stretch)


class TransfersDatabaseTreeView(QTreeView):
    context_selections = Signal(object, object, set)

    def __init__(self, *, parent=None):
        super().__init__(parent)
        self.setUniformRowHeights(True)
        self.setAnimated(False)
        self.resizeColumnToContents(0)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setUniformRowHeights(True)
        self.setTextElideMode(Qt.ElideMiddle)
        delegate = ProgressBarDelegate(self)
        self.setItemDelegateForColumn(3, delegate)

    def setup_header(self):
        # columns (original (get updated before moving))
        # (RECHECK)
        pk_col = 0
        source_col = 1
        destination_col = 2
        # progress_col = 3
        priority_col = 6
        status_col = 7
        end_time_col = 9
        error_message_col = 10
        source_type_col = 11
        dest_type_col = 12
        # status | destination | pbar | rate | size | status
        header = QHeaderView(Qt.Horizontal)
        self.setHeader(header)
        # header.setSectionResizeMode(source_col, QHeaderView.Stretch)
        # header.setSectionResizeMode(destination_col, QHeaderView.Stretch)
        # header.setSectionResizeMode(progress_col, QHeaderView.Stretch)
        header.resizeSection(source_col, 200)
        header.resizeSection(destination_col, 200)
        header.setSectionHidden(pk_col, True)
        header.setSectionHidden(end_time_col, True)
        header.setSectionHidden(status_col, True)
        header.setSectionHidden(priority_col, True)
        header.setSectionHidden(error_message_col, True)
        header.setSectionHidden(source_type_col, True)
        header.setSectionHidden(dest_type_col, True)

    def contextMenuEvent(self, event):
        processed = set()
        index_heap = []
        for index in self.selectedIndexes():
            if index.row() not in processed:
                heapq.heappush(index_heap, (index.row(), index))
                processed.add(index.row())
        if index_heap:
            self.context_selections.emit(
                self, event.globalPos(), [i for _, i in index_heap]
            )


class ResultsDatabaseTreeView(QTreeView):

    def __init__(self, *, parent=None):
        super().__init__(parent)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setSortingEnabled(True)

    def setup_header(self):
        header = QHeaderView(Qt.Horizontal)
        self.setHeader(header)
        # Since there are no custom columns, these stay true to the DB
        header.setSectionHidden(0, True)
        header.setSectionHidden(4, True)
        header.setSectionHidden(5, True)
        header.setSectionHidden(8, True)
        # header.setSectionResizeMode(1, QHeaderView.Stretch)
        # header.setSectionResizeMode(2, QHeaderView.Stretch)
