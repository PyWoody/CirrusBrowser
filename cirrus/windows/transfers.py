from functools import partial

from cirrus import exceptions, utils, menus

from cirrus.items import TransferItem
from cirrus.models import (
    CompletedTableModel,
    ErrorsTableModel,
    TransfersTableModel,
)
from cirrus.statuses import TransferStatus
from cirrus.views.transfers import (
    ErrorsDatabaseTreeView,
    ResultsDatabaseTreeView,
    TransfersDatabaseTreeView,
)

from PySide6.QtCore import Slot, QThreadPool, QTimer
from PySide6.QtSql import QSqlDatabase
from PySide6.QtWidgets import QMenu, QTabWidget, QVBoxLayout, QWidget


class TransfersWindow(QWidget):

    def __init__(self, *, database_queue, parent=None):
        super().__init__(parent)
        self.database_queue = database_queue
        self.last_select = utils.date.epoch()

        con = QSqlDatabase.database('con')
        if not con.open():
            raise exceptions.DatabaseClosedException
        self.transfers = TransfersDatabaseTreeView()
        model = TransfersTableModel(con_name='transfer_con')
        model.select()
        self.transfers.setModel(model)
        self.transfers.setup_header()
        self.transfers.context_selections.connect(self.transfers_context_menu)

        self.errors = ErrorsDatabaseTreeView()
        model = ErrorsTableModel(con_name='error_con')
        model.select()
        self.errors.setModel(model)
        self.errors.setup_header()

        self.results = ResultsDatabaseTreeView()
        model = CompletedTableModel(con_name='completed_con')
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
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

    @Slot(object, object, list)
    def transfers_context_menu(self, parent, pos, indexes):
        menu = QMenu(parent)
        menus.transfer_listing_menu(menu, parent, indexes)
        menu.triggered.connect(self.transfer_menu_item_selected)
        menu.popup(pos)

    def transfer_menu_item_selected(self, action):
        widget = action.parent
        runnable = action.runnable()
        runnable.signals.select.connect(widget.model().select)
        runnable.signals.error.connect(print)
        # runnable.signals.update.connect(self.database_queue.remove_item)
        runnable.signals.ss_callback.connect(utils.execute_ss_callback)
        runnable.signals.callback.connect(utils.execute_callback)
        runnable.signals.finished.connect(print)
        QThreadPool().globalInstance().start(runnable)

    @Slot()
    def select_current_tab_model(self):
        self.tabs.currentWidget().model().select()

    @Slot(TransferItem)
    def select_row(self, item):
        self.transfers.model().selectRow(item.row)

    @Slot(list)
    def select_started_rows(self, transfer_items, start_col=8):
        widget = self.tabs.currentWidget()
        if widget is self.transfers:
            model = widget.model()
            for item in transfer_items:
                model.set_data_by_pk(item.pk, start_col, item.started)

    @Slot(list)
    def select_completed_rows(self, transfer_items):
        widget = self.tabs.currentWidget()
        model = widget.model()
        if (utils.date.now() - model.last_invalidate).seconds > 3:
            if widget is self.transfers:
                model.select()
            elif widget is self.errors:
                if any(
                    i.status == TransferStatus.ERROR for i in transfer_items
                ):
                    model.select()
            elif widget is self.results:
                if any(
                    i.status == TransferStatus.COMPLETED
                    for i in transfer_items
                ):
                    model.select()
        for item in transfer_items:
            QTimer.singleShot(
                0, partial(self.remove_transfer_item, item)
            )

    @Slot(TransferItem)
    def attach_transfer_item(self, item):
        self.transfers.model().transfer_items[item.pk] = item

    @Slot(TransferItem)
    def remove_transfer_item(self, item):
        self.transfers.model().transfer_items.pop(item.pk, None)
