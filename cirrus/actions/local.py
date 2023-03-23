import os
import uuid


from cirrus import database, exceptions, items, settings
from cirrus.actions.signals import ActionSignals

from PySide6.QtGui import QAction
from PySide6.QtCore import QRunnable, Slot
from PySide6.QtSql import QSqlDatabase


class ExampleActionRunnable(QAction):

    def __init__(self, parent, files, destination, overwrite=False):
        super().__init__(parent)
        self.files = files
        self.destination = destination
        self.overwrite = overwrite
        self.runnable = SomeBaseRunnable(
            files, destination, overwrite=overwrite
        )
        self.setText('Example Menu Text')
        self.setStatusTip('Example Status Tip')

    def runnable(self):
        return SomeBaseRunnable()


class SomeBaseRunnable(QRunnable):

    def __init__(self, *args, **kwargs):
        super().__init__()
        self.signals = ActionSignals()
        self._id = str(uuid.uuid4())
        self.args = args
        self.kwargs = kwargs
        self.cancelled = False

    @Slot()
    def run(self):
        self.signals.started.emit()


class FilterAction(QAction):

    def __init__(self, parent, files, folders, destinations):
        super().__init__(parent)
        self.files = files
        self.folders = folders
        self.destination = destinations
        self.setText('Advanced (Filter)')
        self.setStatusTip(
            'Advanced controls for filtering with additional options'
        )

    def runnable(self):
        return FilterRunnable(
            self.root, self.files, self.folders, self.destinations
        )


class FilterRunnable(QRunnable):

    def __init__(self, root, files, folders, destinations, process=False):
        super().__init__()
        self.process = process
        self.signals = ActionSignals()
        self.root = root
        self.files = files
        self.destination = destinations
        self._id = str(uuid.uuid4())

    @Slot()
    def run(self):
        # TODO: Create pop-up window, etc.
        # self.signals.started.emit()
        self.signals.started.emit(f'Testing - {self.root} - START')
        if self.process:
            self.signals.process_queue.emit()
        self.signals.finished.emit(f'Testing - {self.root} - FINISHED')


class CopyMixedItemsAction(QAction):

    def __init__(self, parent, files, folders, destination):
        super().__init__(parent)
        plural_file = 's' if len(files) > 1 else ''
        plural_folder = 's' if len(folders) > 1 else ''
        self.root = parent.root
        self.files = files
        self.folders = folders
        self.destination = destination
        self.setText(f'Selection >> {self.destination}')
        self.setStatusTip(
            f'Copies the selected Folder{plural_folder} '
            f'and File{plural_file} to {self.destination}'
        )

    def runnable(self):
        return MixedItemsRunnable(
            self.root, self.files, self.folders, self.destination, process=True
        )


class CopyFolderAction(QAction):

    def __init__(self, parent, source, destination):
        super().__init__(parent)
        self.destination = destination
        self.root = source.root
        self.setText(f'{self.root} >> {self.destination}')
        self.setStatusTip(
            f'Recursively copies the Files found in {self.root} '
            f'to {self.destination}'
        )

    def runnable(self):
        return FolderRunnable(self.root, self.destination, process=True)


class CopyFoldersAction(QAction):

    def __init__(self, parent, folders, destination):
        super().__init__(parent)
        self.root = parent.root
        self.folders = folders
        self.destination = destination
        self.setText(f'Folders >> {self.destination}')
        self.setStatusTip(
              'Recursively copies the Files found in the selected '
              f'Folders to {self.destination}'
        )

    def runnable(self):
        return FoldersRunnable(
            self.root, self.folders, self.destination, process=True
        )


class CopyFilesAction(QAction):

    def __init__(self, parent, files, destination):
        super().__init__(parent)
        plural = 's' if len(files) > 1 else ''
        self.root = parent.root
        self.files = files
        self.destination = destination
        self.setText(f'Selected File{plural} >> {self.destination}')
        self.setStatusTip(
            f'Copies the selected File{plural} to {self.destination}'
        )

    def runnable(self):
        return FilesRunnable(
            self.root, self.files, self.destination, process=True
        )


class QueueFilesAction(QAction):

    def __init__(self, parent, files, destination):
        super().__init__(parent)
        plural = 's' if len(files) > 1 else ''
        self.root = parent.root
        self.files = files
        self.destination = destination
        self.setText(f'Selected File{plural} >> {self.destination}')
        self.setStatusTip(
            f'Adds the selected File{plural} to the '
            f'queue to be copied to {self.destination}'
        )

    def runnable(self):
        return FilesRunnable(
            self.root, self.files, self.destination
        )


class QueueFolderAction(QAction):

    def __init__(self, parent, source, destination):
        super().__init__(parent)
        self.destination = destination
        self.root = source.root
        self.setText(f'{self.root} >> {self.destination}')
        self.setStatusTip(
            f'Recursively adds the Files found in {self.root} to the '
            f'queue to be copied to {self.destination}'
        )

    def runnable(self):
        return FolderRunnable(self.root, self.destination)


class QueueFoldersAction(QAction):

    def __init__(self, parent, folders, destination):
        super().__init__(parent)
        self.root = parent.root
        self.folders = folders
        self.destination = destination
        self.setText(f'Folders >> {self.destination}')
        self.setStatusTip(
              'Recursively adds the Files found in the selected '
              f'Folders to be copied to {self.destination}'
        )

    def runnable(self):
        return FoldersRunnable(self.root, self.folders, self.destination)


class QueueMixedItemsAction(QAction):

    def __init__(self, parent, files, folders, destination):
        super().__init__(parent)
        plural_file = 's' if len(files) > 1 else ''
        plural_folder = 's' if len(folders) > 1 else ''
        self.root = parent.root
        self.files = files
        self.folders = folders
        self.destination = destination
        self.setText(f'Selection >> {self.destination}')
        self.setStatusTip(
            f'Add the selected Folder{plural_folder} '
            f'and File{plural_file} to the download '
            f'queue to {self.destination}'
        )

    def runnable(self):
        return MixedItemsRunnable(
            self.root, self.files, self.folders, self.destination
        )


class FolderRunnable(QRunnable):

    def __init__(self, root, destination, process=False):
        super().__init__()
        self.process = process
        self.signals = ActionSignals()
        self.root = root
        # self.folder = folder
        self.destination = destination
        self._id = str(uuid.uuid4())

    def run(self):
        self.signals.started.emit(f'Testing - {self.root} - FOLDERS - STARTED')
        con = QSqlDatabase.addDatabase('QSQLITE', self._id)
        con.setDatabaseName(settings.DATABASE)
        if not con.open():
            raise exceptions.DatabaseClosedException
        processed = 0
        for root, dirs, files in os.walk(self.root):
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
                        if self.process:
                            self.signals.process_queue.emit()
                    else:
                        self.signals.error.emit('ERROR')
                    output = []
                fname = os.path.join(root, f)
                if os.path.isfile(fname):
                    standard_item = items.LocalItem(fname)
                    output.append(standard_item)
                    batch_size += 1
            if output:
                if database.add_transfers(
                    output, destination, con_name=self._id
                ):
                    self.signals.select.emit()
                    if self.process:
                        self.signals.process_queue.emit()
                else:
                    self.signals.error.emit('ERROR')
            processed += batch_size - 1
        if processed:
            self.signals.update.emit(
                f'{processed:,} items were added to the queue.'
            )
        self.signals.select.emit()
        if self.process:
            self.signals.process_queue.emit()
        self.signals.finished.emit(
            f'Testing - {self.root} - FOLDERS - FINISHED'
        )
        con.close()

    def __del__(self):
        QSqlDatabase.removeDatabase(self._id)


class FoldersRunnable(QRunnable):

    def __init__(self, root, folders, destination, process=False):
        super().__init__()
        self.process = process
        self.signals = ActionSignals()
        self.root = root
        self.folders = folders
        self.destination = destination
        self._id = str(uuid.uuid4())

    def run(self):
        # If Copy, a caught start will start the queue processing
        # May have to re-emit start to prevent deadlocks
        self.signals.started.emit(f'Testing - {self.root} - FOLDERS - STARTED')
        con = QSqlDatabase.addDatabase('QSQLITE', self._id)
        con.setDatabaseName(settings.DATABASE)
        if not con.open():
            raise exceptions.DatabaseClosedException
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
                            if self.process:
                                self.signals.process_queue.emit()
                        else:
                            self.signals.error.emit('ERROR')
                        output = []
                    fname = os.path.join(root, f)
                    if os.path.isfile(fname):
                        standard_item = items.LocalItem(fname)
                        output.append(standard_item)
                        batch_size += 1
                if output:
                    if database.add_transfers(
                        output, destination, con_name=self._id
                    ):
                        self.signals.select.emit()
                        if self.process:
                            self.signals.process_queue.emit()
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
        if self.process:
            self.signals.process_queue.emit()
        self.signals.finished.emit(
            f'Testing - {self.root} - FOLDERS - FINISHED'
        )
        con.close()

    def __del__(self):
        QSqlDatabase.removeDatabase(self._id)


class MixedItemsRunnable(QRunnable):

    def __init__(self, root, files, folders, destination, process=False):
        super().__init__()
        self.process = process
        self.signals = ActionSignals()
        self.root = root
        self.files = files
        self.folders = folders
        self.destination = destination
        self._id = str(uuid.uuid4())

    @Slot()
    def run(self):
        # If Copy, a caught start will start the queue processing
        # May have to re-emit start to prevent deadlocks
        self.signals.started.emit(f'Testing - {self.root} - START')
        if self.process:
            self.signals.process_queue.emit()
        con = QSqlDatabase.addDatabase('QSQLITE', self._id)
        con.setDatabaseName(settings.DATABASE)
        if not con.open():
            raise exceptions.DatabaseClosedException
        database.add_transfers(self.files, self.destination, con_name=self._id)
        self.signals.select.emit()
        if self.process:
            self.signals.process_queue.emit()
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
                            if self.process:
                                self.signals.process_queue.emit()
                        else:
                            self.signals.error.emit('ERROR')
                        output = []
                    fname = os.path.join(root, f)
                    if os.path.isfile(fname):
                        standard_item = items.LocalItem(fname)
                        output.append(standard_item)
                        batch_size += 1
                if output:
                    if database.add_transfers(
                        output, destination, con_name=self._id
                    ):
                        self.signals.select.emit()
                        if self.process:
                            self.signals.process_queue.emit()
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
        if self.process:
            self.signals.process_queue.emit()
        self.signals.finished.emit(f'Testing - {self.root} - FINISHED')
        con.close()

    def __del__(self):
        QSqlDatabase.removeDatabase(self._id)


class FilesRunnable(QRunnable):

    def __init__(self, root, files, destination, process=False):
        super().__init__()
        self.process = process
        self.signals = ActionSignals()
        self.root = root
        self.files = files
        self.destination = destination
        self._id = str(uuid.uuid4())

    @Slot()
    def run(self):
        self.signals.started.emit(f'Testing - {self.root} - START')
        if self.process:
            self.signals.process_queue.emit()
        con = QSqlDatabase.addDatabase('QSQLITE', self._id)
        con.setDatabaseName(settings.DATABASE)
        if not con.open():
            raise exceptions.DatabaseClosedException
        database.add_transfers(self.files, self.destination, con_name=self._id)
        self.signals.select.emit()
        self.signals.finished.emit(f'Testing - {self.root} - FINISHED')
        con.close()

    def __del__(self):
        QSqlDatabase.removeDatabase(self._id)
