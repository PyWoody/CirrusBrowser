import logging

from cirrus import database, settings

from PySide6.QtGui import QColor, QPalette
from PySide6.QtSql import QSqlDatabase
from PySide6.QtWidgets import QApplication


logging.basicConfig(
    format='%(asctime)s %(message)s',
    datefmt='%m/%d/%Y %I:%M:%S %p',
    filename=settings.LOG,
    encoding='utf-8',
    filemode='w',
    # level=logging.DEBUG,
    level=logging.INFO,
    # level=logging.WARNING
)


def create_connection():
    database.setup()
    con_names = ['con', 'transfer_con', 'error_con', 'completed_con']
    for con_name in con_names:
        con = QSqlDatabase.addDatabase('QSQLITE', con_name)
        con.setDatabaseName(settings.DATABASE)
        if not con.open():
            database.critical_msg('creating', con.lastError().databaseText())
            return False
    return True


if __name__ == '__main__':
    import sys
    from cirrus.windows.main import MainWindow

    app = QApplication([])
    app.aboutToQuit.connect(app.closeAllWindows)
    if not create_connection():
        sys.exit(1)
    palette = QPalette()
    palette.setColor(
        QPalette.ColorRole.Window, QColor(217, 227, 201, 255)
    )
    palette.setColor(
        QPalette.ColorRole.Text, QColor(42, 56, 40)
    )
    palette.setColor(
        QPalette.ColorRole.Button, QColor(210, 209, 195, 255)
    )
    palette.setColor(
        QPalette.ColorRole.Highlight, QColor(141, 184, 186, 255)
    )
    palette.setColor(
        QPalette.ColorRole.HighlightedText, QColor(84, 100, 68)
    )
    app.setPalette(palette)
    window = MainWindow()
    window.closed.connect(app.closeAllWindows)
    window.show()
    sys.exit(app.exec())
