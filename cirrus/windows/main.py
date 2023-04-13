import logging

from .central import CentralWidgetWindow
from cirrus import actions, database

from PySide6.QtCore import QSize
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMainWindow, QToolBar


class MainWindow(QMainWindow):

    def __init__(self, parent=None):
        super().__init__(parent)
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
        tool_bar.addWidget(
            actions.menus.AddPanelToolButton(self.central_widget)
        )
        tool_bar.addWidget(
            actions.menus.RemovePanelToolButton(self.central_widget)
        )
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
        actions_menu.addAction(toggle_transfers_action)
        actions_menu.addAction(toggle_transfers_panel_action)

        edit_menu = menu.addMenu('&Edit')
        help_menu = menu.addMenu('&Help')

        self.resize(900, 700)

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
