import uuid


from .signals import ActionSignals
from cirrus import exceptions, settings

from PySide6.QtGui import QAction
from PySide6.QtCore import QRunnable, Slot
from PySide6.QtSql import QSqlDatabase


class QueueFilesAction(QAction):

    def __init__(self, parent, files, destination):
        super().__init__(parent)
        plural = 's' if len(files) > 1 else ''
        self.setText(f'Add File{plural} to Queue - {destination}')
        self.setStatusTip(
            f'Adds the selected File{plural} to the download queue to be '
            f'downloaded to {destination}'
        )
        self.root = parent.root
        self.files = files
        self.destination = destination

    def runnable(self):
        return QueueFilesRunnable(
            self.root, self.files, self.destination
        )


class QueueFilesRunnable(QRunnable):

    def __init__(self, root, files, destination):
        super().__init__()
        self.signals = ActionSignals()
        self.root = root
        self.files = files
        self.destination = destination
        self._id = str(uuid.uuid4())

    @Slot()
    def run(self):
        self.signals.started.emit(f'Testing - {self.root} - START')
        con = QSqlDatabase.addDatabase('QSQLITE', self._id)
        con.setDatabaseName(settings.DATABASE)
        if not con.open():
            raise exceptions.DatabaseClosedException
        # database.add_transfers(
        #     self.files, self.destination, con_name=self._id
        # )
        print(self.files, self.destination, self._id)
        self.signals.select.emit()
        self.signals.finished.emit(f'Testing - {self.root} - FINISHED')
        con.close()

    def __del__(self):
        QSqlDatabase.removeDatabase(self._id)


class QueueFoldersAction(QAction):

    def __init__(self, parent, folders, destination):
        super().__init__(parent)
        plural = 's' if len(folders) > 1 else ''
        self.setText(f'Add Folder{plural} to Queue')
        self.setStatusTip(
             ('Recursively adds the Files found in the '
              f'Folder{plural} to the download queue')
        )
        self.root = parent.root
        self.folders = folders
        self.destination = destination

    def runnable(self):
        return QueueFoldersRunnable(self.root, self.folders, self.destination)


class QueueFoldersRunnable(QRunnable):

    def __init__(self, root, folders, destination):
        super().__init__()
        self.root = root
        self.folders = folders
        self.destination = destination
        self.signals = ActionSignals()
        self._id = str(uuid.uuid4())

    def run(self):
        self.signals.started.emit(f'Testing - {self.root} - FOLDERS - STARTED')
        con = QSqlDatabase.addDatabase('QSQLITE', self._id)
        con.setDatabaseName(settings.DATABASE)
        if not con.open():
            raise exceptions.DatabaseClosedException
        '''
        for root_item in self.folders:
            processed = 0
            for root, dirs, files in os.walk(root_item.root):
                destination = os.path.abspath(
                    os.path.join(
                        self.destination,
                        os.path.relpath(root, start=self.root)
                    )
                )
                batch_size = 1
                output = []
                for f in files:
                    if batch_size % 100 == 0:
                        if database.add_transfers(
                            output, destination, con_name=self._id
                        ):
                            self.signals.select.emit()
                        else:
                            self.signals.error.emit('ERROR')
                        output = []
                    fname = os.path.join(root, f)
                    if os.path.isfile(fname):
                        standard_item = LocalItemData(
                            fname, size=os.stat(fname).st_size
                        )
                        output.append(standard_item)
                        batch_size += 1
                if output:
                    if database.add_transfers(
                        output, destination, con_name=self._id
                    ):
                        self.signals.select.emit()
                    else:
                        self.signals.error.emit('ERROR')
                processed += batch_size - 1
            if processed:
                self.signals.update.emit(f'Added {processed:,} to queue.')
        if processed:
            self.signals.update.emit(
                f'{processed:,} items were added to the queue.'
            )
        self.signals.select.emit()
        '''
        print('DONE')
        self.signals.finished.emit(
            f'Testing - {self.root} - FOLDERS - FINISHED'
        )
        con.close()

    def __del__(self):
        QSqlDatabase.removeDatabase(self._id)
