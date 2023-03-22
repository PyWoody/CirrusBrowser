import logging

from .central import CentralWidgetWindow
from cirrus import database

from PySide6.QtWidgets import QMainWindow


class MainWindow(QMainWindow):

    def __init__(self, parent=None):
        super().__init__(parent)
        logging.info('Resetting the database.')
        if database.clean_database():
            logging.info('Database cleaned.')
        self.central_widget = CentralWidgetWindow()
        self.setCentralWidget(self.central_widget)
        self.resize(900, 700)
        self.status_bar = self.statusBar()
        self.status_bar.showMessage('Status Bar Test')

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
