import logging

from .central import CentralWidgetWindow
from cirrus import actions, database

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
        self.status_bar.showMessage('Status Bar Test')
        tool_bar = QToolBar()
        tool_bar.setMovable(False)
        tool_bar.setFloatable(False)
        tool_bar.addWidget(
            actions.menus.AddPanelToolButton(self.central_widget)
        )
        tool_bar.addWidget(
            actions.menus.RemovePanelToolButton(self.central_widget)
        )
        self.addToolBar(tool_bar)
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
