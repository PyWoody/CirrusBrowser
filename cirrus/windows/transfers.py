
from functools import partial

from cirrus import exceptions, utils, menus

from cirrus.items import TransferItem
from cirrus.models import FinishedTableModel, TransfersTableModel
from cirrus.statuses import TransferStatus
from cirrus.views.transfers import (
    ErrorsDatabaseTreeView,
    ResultsDatabaseTreeView,
    TransfersDatabaseTreeView,
)

from PySide6.QtCore import Slot, Qt, QThreadPool, QTimer
from PySide6.QtSql import QSqlDatabase
from PySide6.QtWidgets import QMenu, QTabWidget, QVBoxLayout, QWidget


class TransfersWindow(QWidget):

    def __init__(self, *, database_queue, parent=None):
        super().__init__(parent)
        self.database_queue = database_queue
        self.threadpool = QThreadPool()
        self.rows_to_be_popped = []
        self.last_select = utils.date.epoch()

        con = QSqlDatabase.database('con')
        if not con.open():
            raise exceptions.DatabaseClosedException
        self.transfers = TransfersDatabaseTreeView()
        model = TransfersTableModel(db=con)
        model.insertColumn(3)
        model.insertColumn(4)
        model.setTable('transfers')
        model.setFilter(
            f'status != {TransferStatus.ERROR.value} '
            f'AND status != {TransferStatus.COMPLETED.value}'
        )
        model.setSort(0, Qt.AscendingOrder)
        model.select()
        self.transfers.setModel(model)
        self.transfers.setup_header()
        self.transfers.context_selections.connect(self.transfers_context_menu)

        self.errors = ErrorsDatabaseTreeView()
        # model = ErrorsTableModel(db=con)
        model = FinishedTableModel(db=con)
        model.setTable('transfers')
        model.setFilter(f'status = {TransferStatus.ERROR.value}')
        model.select()
        self.errors.setModel(model)
        self.errors.setup_header()

        self.results = ResultsDatabaseTreeView()
        # model = CompletedTableModel(db=con)
        model = FinishedTableModel(db=con)
        model.setTable('transfers')
        model.setFilter(f'status = {TransferStatus.COMPLETED.value}')
        model.select()
        self.results.setModel(model)
        self.results.setup_header()

        # Stacks on stacks on stacks
        self.tabs = QTabWidget()
        self.tabs.setTabPosition(QTabWidget.TabPosition.South)
        self.tabs.tabBar().setExpanding(True)
        self.tabs.tabBar().setDocumentMode(True)
        self.tabs.addTab(self.transfers, 'Transfers')
        self.tabs.addTab(self.errors, 'Errors')
        self.tabs.addTab(self.results, 'Processed')
        self.tabs.currentChanged.connect(self.select_current_tab_model)
        layout = QVBoxLayout()
        layout.addWidget(self.tabs)
        self.setLayout(layout)

    @Slot(object, object, set)
    def transfers_context_menu(self, parent, pos, indexes):
        menu = QMenu(parent)
        menus.transfer_listing_menu(menu, parent, indexes)
        menu.triggered.connect(self.menu_item_selected)
        menu.popup(pos)

    def menu_item_selected(self, action):
        widget = action.parent
        runnable = action.runnable()
        runnable.signals.started.connect(print)
        runnable.signals.select.connect(widget.model().select)
        runnable.signals.error.connect(print)
        runnable.signals.update.connect(self.database_queue.remove_item)
        runnable.signals.finished.connect(print)
        self.threadpool.start(runnable)

    @Slot(int)
    def select_current_tab_model(self):
        self.tabs.currentWidget().model().select()

    @Slot(TransferItem)
    def select_row(self, item):
        self.transfers.model().selectRow(item.row)

    @Slot(list)
    def select_started_rows(self, transfer_items):
        widget = self.tabs.currentWidget()
        if widget is self.transfers:
            model = widget.model()
            for item in transfer_items:
                QTimer.singleShot(0, partial(model.selectRow, item.row))

    @Slot(list)
    def select_completed_rows(self, transfer_items):
        self.rows_to_be_popped.extend(transfer_items)
        widget = self.tabs.currentWidget()
        model = widget.model()
        if (utils.date.now() - model.last_invalidate).seconds > 3:
            if widget is self.transfers:
                if model.canFetchMore():
                    model.fetchMore()
            elif widget is self.errors:
                for item in transfer_items:
                    if item.status == TransferStatus.ERROR:
                        model.select()
                        break
            elif widget is self.results:
                for item in transfer_items:
                    if item.status == TransferStatus.COMPLETED:
                        model.select()
                        break
            for item in self.rows_to_be_popped:
                QTimer.singleShot(
                    0, partial(self.remove_transfer_item, item)
                )
            self.rows_to_be_popped.clear()

    @Slot(TransferItem)
    def attach_transfer_item(self, item):
        self.transfers.model().transfer_items[item.pk] = item

    @Slot(TransferItem)
    def remove_transfer_item(self, item):
        self.transfers.model().transfer_items.pop(item.pk, None)
