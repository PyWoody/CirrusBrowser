import logging
from functools import partial

from .central import CentralWidgetWindow
from cirrus import actions, database

from PySide6.QtCore import QSize, Qt, Signal, Slot
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import QMainWindow, QToolBar


class MainWindow(QMainWindow):
    closed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setWindowTitle('Cirrus Browser (Experimental)')
        logging.info('Resetting the database.')
        if database.clean_database():
            logging.info('Database cleaned.')

        self.central_widget = CentralWidgetWindow()
        self.setCentralWidget(self.central_widget)

        self.status_bar = self.statusBar()

        # Actions
        toggle_transfers_action = actions.menus.ToggleProcessingTransfers(
            self.central_widget
        )
        toggle_transfers_action.triggered.connect(
            self.central_widget.toggle_timers_flag
        )
        toggle_transfers_panel_action = actions.menus.ToggleTransferPanel(
            self.central_widget
        )
        add_panel_action = actions.menus.AddPanelDefaultAction(
            self.central_widget
        )
        remove_panel_action = actions.menus.RemovePanelDefaultAction(
            self.central_widget
        )

        # Tool bar
        tool_bar = QToolBar()
        tool_bar.setIconSize(QSize(24, 24))
        tool_bar.setMovable(False)
        tool_bar.setFloatable(False)
        self.remove_panel_tool_btn = actions.menus.RemovePanelToolButton(
            self.central_widget
        )
        tool_bar.addWidget(
            actions.menus.AddPanelToolButton(self.central_widget)
        )
        tool_bar.addWidget(self.remove_panel_tool_btn)
        tool_bar.addSeparator()
        tool_bar.addAction(toggle_transfers_action)
        tool_bar.addAction(toggle_transfers_panel_action)
        self.addToolBar(tool_bar)

        # Menu Bar
        menu = self.menuBar()

        file_menu = menu.addMenu('&File')
        file_menu.addAction(add_panel_action)
        file_menu.addAction(remove_panel_action)
        file_menu.addSeparator()
        exit_action = QAction('Exit', self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        actions_menu = menu.addMenu('&Actions')
        search_all_action = actions.search.SearchAllAction(self)
        search_all_action.triggered.connect(search_all_action.show_dialog)
        search_all_action.accepted.connect(
            partial(
                self.central_widget.menu_item_selected_cb, search_all_action
            )
        )
        actions_menu.addAction(search_all_action)
        actions_menu.addMenu(
            actions.menus.BuildSearchMenu(self.central_widget)
        )
        actions_menu.addAction(toggle_transfers_action)
        actions_menu.addAction(toggle_transfers_panel_action)

        menu.addMenu('&Edit')
        menu.addMenu('&Help')

        self.central_widget.listing_panel_added.connect(
            self.track_add_panel_action
        )
        self.central_widget.listing_panel_removed.connect(
            self.track_remove_panel_action
        )

        self.resize(900, 700)

    def keyPressEvent(self, event):
        key_combo = event.keyCombination().toCombined()
        if key_combo == QKeySequence(Qt.CTRL | Qt.Key_F):
            action = actions.search.SearchAllAction(self)
            action.accepted.connect(
                partial(self.central_widget.menu_item_selected_cb, action)
            )
            action.show_dialog()
        elif key_combo == QKeySequence(Qt.CTRL | Qt.Key_N):
            self.central_widget.setup_login()
        elif key_combo == QKeySequence(Qt.CTRL | Qt.Key_W):
            self.close()
        else:
            return super().keyPressEvent(event)

    def closeEvent(self, event):
        try:
            if self.central_widget.executor is not None:
                logging.info('Shutting down executor.')
                self.central_widget.executor.shutdown()
                logging.info('Executor shutdown.')
            logging.info('Resetting the database.')
            if database.clean_database():
                logging.info('Database cleaned.')
            else:
                logging.info('Database was not properly cleaned.')
        except Exception as e:
            database.critical_msg('closeEvent', str(e))
        finally:
            super().closeEvent(event)
            self.closed.emit()

    @Slot(int)
    def track_add_panel_action(self, index):
        if not self.remove_panel_tool_btn.isEnabled():
            self.remove_panel_tool_btn.setEnabled(True)

    @Slot(int)
    def track_remove_panel_action(self, index):
        if not self.central_widget.splitter_listing_panels:
            if self.remove_panel_tool_btn.isEnabled():
                self.remove_panel_tool_btn.setEnabled(False)
