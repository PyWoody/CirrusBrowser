import uuid

from cirrius import exceptions, settings
from cirrus.actions.signals import ActionSignals

from PySide6.QtGui import QAction
from PySide6.QtCore import QRunnable
from PySide6.QtSql import QSqlDatabase

class DropRowsAction(QAction):

    def __init__(self, parent, indexes):
        super().__init__(parent)
        self.parent = parent
        self.indexes = indexes
        self.setText('Remove selection')
        self.setStatusTip('Removes the selected rows from the database.')

    def runnable(self):
        return DropRowsRunnable(self.parent, self.indexes)


class DropRowsRunnable(QRunnable):

    def __init__(self, parent, indexes):
        super().__init__()
        self.parent = parent
        self.signals = ActionSignals()
        self.indexes = indexes
        self._id = str(uuid.uuid4())

    def run(self):
        # TODO: Items could still be in the database.hot_queue
        con = QSqlDatabase.addDatabase('QSQLITE', self._id)
        con.setDatabaseName(settings.DATABASE)
        if not con.open():
            raise exceptions.DatabaseClosedException
        for index in self.indexes:
            root = index.siblingAtColumn(1).data()
            if self.parent.model().removeRow(index.row()):
                self.signals.update.emit(root)
            else:
                self.signals.error.emit(f'Failed to drop row: {index.row()}')
        self.signals.select.emit()
        self.signals.finished.emit('Finished drop')
        self.parent.model().submitAll()
        con.close()

    def __del__(self):
        QSqlDatabase.removeDatabase(self._id)
