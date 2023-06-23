import logging
import os

from datetime import datetime
from functools import partial

from .login import LoginWindow
from .transfers import TransfersWindow
from cirrus import database, items, menus, settings, utils, windows
from cirrus.executor import Executor
from cirrus.statuses import TransferStatus

from PySide6.QtCore import (
    Qt,
    QTimer,
    QThreadPool,
    Signal,
    Slot,
)
from PySide6.QtWidgets import (
    QMenu,
    QSplitter,
    QVBoxLayout,
    QWidget,
)


class CentralWidgetWindow(QWidget):  # Terrible name

    listing_panel_removed = Signal(int)
    listing_panel_added = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.threadpool = QThreadPool()
        self.last_select = utils.date.epoch()
        self.database = database.Database()
        self.database.start()

        self.num_current_transfers = 0
        self.__started_transfers_to_update = []
        self.__error_transfers_to_update = []
        self.__completed_transfers_to_update = []

        # setup DB names
        # Terrible name. Need to re-evaluate
        self.database_queue = database.DatabaseQueue()
        self.database_queue.build_queue()

        # Transfers/Errors/Results Window
        self.transfers_window = TransfersWindow(
            database_queue=self.database_queue
        )
        if settings.transfer_window_visible():
            self.transfers_window.show()
        else:
            self.transfers_window.hide()
        self.database_queue.completed.connect(
            self.transfers_window.transfers.model().select
        )

        # Views
        # Files View (Splittable)
        # TODO: Utilie the saveState, getState from QSplitter
        self.splitter_listing_panels = []
        self.listings_view_splitter = QSplitter()
        self.listings_view_splitter.setChildrenCollapsible(False)
        self.listings_view_splitter.setOpaqueResize(True)

        # Executor
        self.current_transfers = set()
        self.max_workers = 10  # will be an input
        self.executor = Executor(
            self.database_queue, max_workers=self.max_workers
        )
        self.executor.started.connect(
            self.transfers_window.attach_transfer_item
        )
        self.executor.started.connect(self.transfer_started)
        self.executor.finished.connect(self.transfer_finished)
        self.executor.stopped.connect(database.restart_queued_transfer)
        self.executor.stopped.connect(
            self.transfers_window.remove_transfer_item
        )
        self.executor.stopped.connect(self.transfers_window.select_row)

        # Timers
        self.update_timer = QTimer()
        self.update_timer.setInterval(1_000)
        self.update_timer.timeout.connect(self.update_transfering_rows)
        self.update_timer.start()

        self.batch_start_timer = QTimer()
        self.batch_start_timer.setInterval(1_000)
        self.batch_start_timer.timeout.connect(self.batch_started_db_update)
        self.batch_start_timer.start()

        self.batch_finished_timer = QTimer()
        self.batch_finished_timer.setInterval(1_000)
        self.batch_finished_timer.timeout.connect(
            self.batch_completed_db_update
        )
        self.batch_finished_timer.start()

        # Should this be a QSplitter instead?
        layout = QVBoxLayout()
        views_layout = QSplitter()
        views_layout.setOrientation(Qt.Vertical)
        views_layout.addWidget(self.listings_view_splitter)
        views_layout.addWidget(utils.HLine())
        views_layout.addWidget(self.transfers_window)
        layout.addWidget(views_layout)
        self.setLayout(layout)
        self.last_updated = datetime.utcnow()
        self.setup_initial_splitter_panels()

    def setup_login(self):
        login = LoginWindow(self)
        login.setModal(True)
        login.account_selected.connect(self.add_splitter_panels)
        login.show()

    def listing_context_menu(self, parent, pos, files, folders):
        # TODO: Tristate selections in none selected view
        # TODO: Doesn't this need a slot?
        panels = [
            window.view for window, _ in self.splitter_listing_panels
        ]
        menu = QMenu(parent)
        # TODO: Create a top-level menu here and add all other menus
        #       as subMenus. Pass the menu in as an arg
        # TODO: Add finer grained options, such as selective/filtered
        #       Queued or downloads
        menus.file_listing_menu(
            menu, parent, files, folders, panels
        )
        menu.triggered.connect(self.menu_item_selected)
        menu.popup(pos)

    def menu_item_selected(self, action):
        model = self.transfers_window.tabs.currentWidget().model()
        if action.show_dialog():
            action.accepted.connect(
                partial(
                    self.menu_item_selected_cb, action, model
                )
            )
        else:
            self.menu_item_selected_cb(action, model)

    def menu_item_selected_cb(self, action, model=None):
        runnable = action.runnable()
        runnable.signals.aborted.connect(partial(print, 'Aborted!'))
        runnable.signals.update.connect(print)
        runnable.signals.process_queue.connect(self.start_queue_tmp)
        if model is not None:
            runnable.signals.select.connect(model.select)
        runnable.signals.ss_callback.connect(utils.execute_ss_callback)
        runnable.signals.callback.connect(utils.execute_callback)
        runnable.signals.finished.connect(print)
        self.threadpool.start(runnable)

    def s3_context_menu(self, parent, pos, files, folders):
        raise NotImplementedError
        context = menus.local_file_listing_menu(
            parent, files, folders, parent.root
        )
        context.triggered.connect(self.menu_item_selected)
        context.popup(pos)

    def start_queue_tmp(self, start):
        print('start_queue_tmp called:', start)
        if start:
            pass

    def setup_initial_splitter_panels(self):
        last_open_panels = [p for p in settings.saved_panels()]
        if last_open_panels:
            self.add_previous_splitter_panels(last_open_panels)
        else:
            user = settings.new_user(
                act_type='Local',
                root=os.path.expanduser('~'),
                nickname='Home',
            )
            settings.update_saved_users(user)
            self.add_splitter_panel(user)

    @Slot(list)
    def add_previous_splitter_panels(self, accounts):
        for account in accounts:
            self.add_splitter_panel(account, existing_panel=True)

    @Slot(list)
    def add_splitter_panels(self, accounts):
        for account in accounts:
            self.add_splitter_panel(account)

    def add_splitter_panel(self, account, existing_panel=False):
        if listing := windows.types.get(account['Type'].lower()):
            window = listing(account)
            window.setMinimumSize(350, 250)
        else:
            logging.warn(f'No valid Type found for {account}')
            return
        window.view.context_selections.connect(self.listing_context_menu)
        self.splitter_listing_panels.append((window, account))
        root_change_cb = settings.update_panel_by_index_cb(
            panel=account,
            index=len(self.splitter_listing_panels) - 1,
            key='Root'
        )
        window.view.root_changed.connect(root_change_cb)
        self.listings_view_splitter.addWidget(window)
        if (index := self.listings_view_splitter.indexOf(window)) > 0:
            self.listings_view_splitter.insertWidget(index, utils.VLine())
        if not existing_panel:
            settings.append_panel(account)
        self.listing_panel_added.emit(index)

    @Slot()
    def pop_splitter_panel(self):
        if self.splitter_listing_panels:
            window, account = self.splitter_listing_panels.pop()
            if (index := self.listings_view_splitter.indexOf(window)) > 0:
                if splitter := self.listings_view_splitter.widget(index - 1):
                    if isinstance(splitter, utils.VLine):
                        splitter.hide()
                        splitter.setParent(None)
                        splitter = None
                        del splitter
            settings.pop_saved_panel()
            window.hide()
            window.setParent(None)
            window = None
            del window
            self.listing_panel_removed.emit(index)

    @Slot(int)
    def remove_splitter_panel(self, index):
        try:
            window, account = self.splitter_listing_panels.pop(index)
        except IndexError:
            pass
        else:
            index = self.listings_view_splitter.indexOf(window)
            count = self.listings_view_splitter.count()
            splitter_index = index + 1 if index + 1 != count else index - 1
            if splitter := self.listings_view_splitter.widget(splitter_index):
                if isinstance(splitter, utils.VLine):
                    splitter.hide()
                    splitter.setParent(None)
                    splitter = None
                    del splitter
            settings.remove_saved_panel(account)
            window.hide()
            window.setParent(None)
            window = None
            del window
            self.listing_panel_removed.emit(index)

    @Slot(object)
    def time_delta_select(self, widget):
        current_pos = widget.verticalScrollBar().value() + 1
        max_pos = widget.verticalScrollBar().maximum() + 1
        if current_pos / max_pos > .75:
            QTimer.singleShot(0, widget.model().delta_select)

    @Slot()
    def update_transfering_rows(self):
        QTimer.singleShot(0, self.__update_transfering_rows)

    def __update_transfering_rows(self):
        if self.current_transfers:
            current_widget = self.transfers_window.tabs.currentWidget()
            transfers = self.transfers_window.transfers
            if current_widget is transfers:
                model = transfers.model()
                QTimer.singleShot(
                    0,
                    partial(
                        model.dataChanged.emit,
                        model.index(0, 3),
                        model.index(self.num_current_transfers, 4),
                        [Qt.DisplayRole],
                    )
                )
                logging.debug(
                    ('dataChanged emitted for '
                     f'{len(self.current_transfers)} rows')
                )

    @Slot()
    def toggle_transfer_window(self):
        if self.transfers_window.isVisible():
            self.transfers_window.hide()
            settings.update_transfer_window_status(False)
        else:
            self.transfers_window.show()
            settings.update_transfer_window_status(True)

    @Slot(items.TransferItem)
    def transfer_started(self, item):
        self.num_current_transfers += 1
        self.__started_transfers_to_update.append(item)
        self.current_transfers.add(item)

    @Slot(items.TransferItem)
    def transfer_finished(self, item):
        self.num_current_transfers -= 1
        if item in self.current_transfers:
            _ = self.current_transfers.remove(item)
        if item.status == TransferStatus.ERROR:
            self.__error_transfers_to_update.append(item)
        else:
            self.__completed_transfers_to_update.append(item)

    def batch_started_db_update(self):
        if self.__started_transfers_to_update:
            logging.debug(
                (f'Sending {len(self.__started_transfers_to_update)} '
                 'items to `database.started_batch_update`')
            )
            response = database.started_batch_update(
                self.__started_transfers_to_update
            )
            if not response:
                logging.warn(
                    ('Failed to send '
                     f'{len(self.__started_transfers_to_update)} '
                     'items to `database.started_batch_update`')
                )
            logging.debug(
                (f'Sent {len(self.__started_transfers_to_update)} '
                 'items to `database.started_batch_update`')
            )
            logging.debug(
                (f'Selecting {len(self.__started_transfers_to_update)} '
                 'started rows')
            )
            self.transfers_window.select_started_rows(
                self.__started_transfers_to_update
            )
            logging.debug(
                (f'Selected {len(self.__started_transfers_to_update)} '
                 'started rows')
            )
            self.__started_transfers_to_update.clear()

    def batch_completed_db_update(self):
        # TODO: Manual calls to the DB shoul be done via the model's setData
        output = []
        if self.__error_transfers_to_update:
            output.extend(self.__error_transfers_to_update)
            logging.debug(
                (f'Sending {len(self.__error_transfers_to_update)} '
                 'to `database.error_batch_update`')
            )
            response = database.error_batch_update(
                self.__error_transfers_to_update
            )
            if not response:
                logging.warn(
                    ('Failed to send '
                     f'{len(self.__error_transfers_to_update)} '
                     'to `database.error_batch_update`')
                )
            logging.debug(
                (f'Sent {len(self.__error_transfers_to_update)} '
                 'to `database.error_batch_update`')
            )
            output.extend(self.__error_transfers_to_update)
            self.__error_transfers_to_update.clear()
        if self.__completed_transfers_to_update:
            output.extend(self.__completed_transfers_to_update)
            logging.debug(
                (f'Sending {len(self.__completed_transfers_to_update)} '
                 'to `database.completed_batch_update`')
            )
            response = database.completed_batch_update(
                self.__completed_transfers_to_update
            )
            if not response:
                logging.warn(
                    ('Failed to send '
                     f'{len(self.__completed_transfers_to_update)} '
                     'to `database.completed_batch_update`')
                )
            logging.debug(
                (f'Sent {len(self.__completed_transfers_to_update)} '
                 'to `database.completed_batch_update`')
            )
            output.extend(self.__completed_transfers_to_update)
            self.__completed_transfers_to_update.clear()
        if output:
            logging.debug(f'Selecting {len(output)} completed rows')
            self.transfers_window.select_completed_rows(output)
            logging.debug(f'Selected {len(output)} completed rows')
            output.clear()
