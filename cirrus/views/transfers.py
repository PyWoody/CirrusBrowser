import heapq
import time

from functools import partial

from cirrus import utils
from cirrus.delegates import ProgressBarDelegate

from PySide6.QtCore import (
    QItemSelectionModel,
    QItemSelection,
    QModelIndex,
    Qt,
    QTimer,
    Signal,
    Slot,
)
from PySide6.QtGui import QContextMenuEvent, QKeyEvent, QKeySequence
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
        self.shift_down = False
        self.ctrl_down = False
        self.last_selected_index = QModelIndex()
        self.selected_indexes = set()
        self.clicked.connect(self.update_selected_indexes)

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

    @Slot(QKeyEvent)
    def keyPressEvent(self, event):
        key_combo = event.keyCombination().toCombined()
        if key_combo == QKeySequence(Qt.CTRL | Qt.Key_A):
            self.select_all()
        else:
            if event.key() == Qt.Key_Shift:
                self.shift_down = True
            elif event.key() == Qt.Key_Control:
                self.ctrl_down = True
            super().keyPressEvent(event)

    @Slot(QKeyEvent)
    def keyReleaseEvent(self, event):
        self.shift_down = False
        self.ctrl_down = False
        return super().keyReleaseEvent(event)

    @utils.long_running_action()
    def select_all(self):
        model = self.model()
        selection_model = self.selectionModel()
        group = []
        for row in range(model.rowCount()):
            item = model.index(row, 0)
            if item.isValid() and not selection_model.isSelected(item):
                self.selected_indexes.add(item)
                group.append(item)
                if len(group) % 100 == 0:
                    QTimer.singleShot(
                        0,
                        partial(
                            selection_model.select,
                            QItemSelection(group[0], group[-1]),
                            QItemSelectionModel.Rows | QItemSelectionModel.Select
                        )
                    )
                    group = []
        if group:
            QTimer.singleShot(
                0,
                partial(
                    selection_model.select,
                    QItemSelection(group[0], group[-1]),
                    QItemSelectionModel.Rows | QItemSelectionModel.Select
                )
            )

    @Slot(QModelIndex)
    def update_selected_indexes(self, index):
        if index.isValid():
            if self.shift_down and self.last_selected_index.isValid():
                if index.row() > self.last_selected_index.row():
                    indexes_range = range(
                        self.last_selected_index.row(), index.row()
                    )
                else:
                    indexes_range = range(
                        index.row(), self.last_selected_index.row()
                    )
                for row in indexes_range:
                    self.selected_indexes.add(self.model().index(row, 0))
            elif self.ctrl_down:
                self.selected_indexes.add(index)
            else:
                self.selected_indexes = {index}
            self.last_selected_index = index

    @Slot(QContextMenuEvent)
    def contextMenuEvent(self, event):
        index_heap = []
        updated_cursor = False
        epoch = time.time()
        for index in self.selected_indexes:
            if not updated_cursor and (time.time() - epoch) > 0.1:
                self.setCursor(Qt.WaitCursor)
                updated_cursor = True
            heapq.heappush(index_heap, (index.row(), index))
        if updated_cursor:
            self.setCursor(Qt.ArrowCursor)
        if index_heap:
            self.context_selections.emit(
                self,
                event.globalPos(),
                [heapq.heappop(index_heap)[1] for _ in range(len(index_heap))]
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
