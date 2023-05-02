import os
import uuid

from functools import partial

from .base import BaseAction, BaseRunnable
from cirrus import database, dialogs, exceptions, items, settings, utils
from cirrus.actions.signals import ActionSignals

from PySide6.QtCore import Slot
from PySide6.QtGui import QIcon
from PySide6.QtSql import QSqlDatabase


class CreateDirectoryAction(BaseAction):

    def __init__(self, parent, folders=None):
        super().__init__(parent)
        # TODO: Accept selected folder for parent.root, folder, input
        self.dialog = None
        self.parent = parent
        self.folders = folders
        self.setIcon(QIcon(os.path.join(settings.ICON_DIR, 'add-folder.svg')))
        self.setText('Create Directory')
        self.setStatusTip('Create a directory from the current location.')

    def show_dialog(self, *args, **kwargs):
        self.dialog = dialogs.CreateDirectoryDialog(
            self.parent, folders=self.folders
        )
        self.dialog.accepted.connect(self.accepted.emit)
        self.dialog.setModal(True)
        self.dialog.show()
        return True

    def runnable(self):
        return CreateDirectoryRunnable(self.parent, self.dialog)


class CopyMixedItemsAction(BaseAction):

    def __init__(self, parent, files, folders, destination):
        super().__init__(parent)
        plural_file = 's' if len(files) > 1 else ''
        plural_folder = 's' if len(folders) > 1 else ''
        self.parent = parent
        self.files = files
        self.folders = folders
        self.destination = destination
        self.setText(f'Selection >> {self.destination.root}')
        self.setStatusTip(
            f'Copies the selected Folder{plural_folder} '
            f'and File{plural_file} to {self.destination.root}'
        )

    def runnable(self):
        return MixedItemsRunnable(
            self.parent,
            self.files,
            self.folders,
            self.destination,
            process=True
        )


class CopyFolderAction(BaseAction):

    def __init__(self, parent, source, destination):
        super().__init__(parent)
        self.destination = destination
        self.parent = parent
        self.source = source
        self.setText(f'{self.parent.root} >> {self.destination.root}')
        self.setStatusTip(
            f'Recursively copies the Files found in {self.parent.root} '
            f'to {self.destination.root}'
        )

    def runnable(self):
        return FolderRunnable(
            self.parent, self.source, self.destination, process=True
        )


class CopyFoldersAction(BaseAction):

    def __init__(self, parent, folders, destination):
        super().__init__(parent)
        self.parent = parent
        self.folders = folders
        self.destination = destination
        self.setText(f'Folders >> {self.destination.root}')
        self.setStatusTip(
              'Recursively copies the Files found in the selected '
              f'Folders to {self.destination.root}'
        )

    def runnable(self):
        return FoldersRunnable(
            self.parent, self.folders, self.destination, process=True
        )


class CopyFilesAction(BaseAction):

    def __init__(self, parent, files, destination):
        super().__init__(parent)
        plural = 's' if len(files) > 1 else ''
        self.parent = parent
        self.files = files
        self.destination = destination
        self.setText(f'Selected File{plural} >> {self.destination.root}')
        self.setStatusTip(
            f'Copies the selected File{plural} to {self.destination.root}'
        )

    def runnable(self):
        return FilesRunnable(
            self.parent, self.files, self.destination, process=True
        )


class QueueFilesAction(BaseAction):

    def __init__(self, parent, files, destination):
        super().__init__(parent)
        plural = 's' if len(files) > 1 else ''
        self.parent = parent
        self.files = files
        self.destination = destination
        self.setText(f'Selected File{plural} >> {self.destination.root}')
        self.setStatusTip(
            f'Adds the selected File{plural} to the '
            f'queue to be copied to {self.destination.root}'
        )

    def runnable(self):
        return FilesRunnable(
            self.parent, self.files, self.destination
        )


class QueueFolderAction(BaseAction):

    def __init__(self, parent, source, destination):
        super().__init__(parent)
        self.destination = destination
        self.parent = parent
        self.source = source
        self.setText(f'{self.parent.root} >> {self.destination.root}')
        self.setStatusTip(
            f'Recursively adds the Files found in {self.parent.root} to the '
            f'queue to be copied to {self.destination.root}'
        )

    def runnable(self):
        return FolderRunnable(self.parent, self.source, self.destination)


class QueueFoldersAction(BaseAction):

    def __init__(self, parent, folders, destination):
        super().__init__(parent)
        self.parent = parent
        self.folders = folders
        self.destination = destination
        self.setText(f'Folders >> {self.destination.root}')
        self.setStatusTip(
              'Recursively adds the Files found in the selected '
              f'Folders to be copied to {self.destination.root}'
        )

    def runnable(self):
        return FoldersRunnable(self.parent, self.folders, self.destination)


class QueueMixedItemsAction(BaseAction):

    def __init__(self, parent, files, folders, destination):
        super().__init__(parent)
        plural_file = 's' if len(files) > 1 else ''
        plural_folder = 's' if len(folders) > 1 else ''
        self.parent = parent
        self.files = files
        self.folders = folders
        self.destination = destination
        self.setText(f'Selection >> {self.destination.root}')
        self.setStatusTip(
            f'Add the selected Folder{plural_folder} '
            f'and File{plural_file} to the download queue to '
            f'{self.destination.root}'
        )

    def runnable(self):
        return MixedItemsRunnable(
            self.parent, self.files, self.folders, self.destination
        )


class RemoveItemsAction(BaseAction):

    def __init__(self, parent, files, folders):
        super().__init__(parent)
        self.parent = parent
        self.dialog = None
        plural_file = 's' if len(files) > 1 else ''
        plural_folder = 's' if len(folders) > 1 else ''
        self.items = files + folders
        help_text = ''
        if folders and files:
            help_text = (f'Delete selected Folder{plural_folder} and '
                         f'selected File{plural_file}')
        elif folders:
            help_text = f'Delete selected Folder{plural_folder}'
        elif files:
            help_text = f'Delete selected File{plural_file}'
        else:
            help_text = 'No selections made'
        self.setText(help_text)
        self.setStatusTip('Delete the selected items')

    def show_dialog(self, *args, **kwargs):
        self.dialog = dialogs.ConfirmDeleteDialog(self.parent)
        self.dialog.accepted.connect(self.accepted.emit)
        self.dialog.setModal(True)
        self.dialog.show()
        return True

    def runnable(self):
        return RemoveItemsRunnable(self.parent, self.items)


class CreateDirectoryRunnable(BaseRunnable):

    def __init__(self, parent, dialog):
        super().__init__()
        self.parent = parent
        self.dialog = dialog
        self.signals = ActionSignals()

    @Slot()
    def run(self):
        self.signals.started.emit()
        item = items.types.get(self.parent.type.lower())
        if not item:
            raise NotImplementedError
        for _, checkbox, label in self.dialog.folder_options:
            if checkbox.isChecked():
                path = utils.html_to_text(label.text())
                user = items.new_user(self.parent.user, path)
                item(user, is_dir=True).makedirs()
        self.signals.finished.emit(f'Testing - {self.parent.root} - FINISHED')
        self.signals.callback.emit(self.parent().refresh)


class FolderRunnable(BaseRunnable):

    def __init__(self, parent, source, destination, process=False):
        super().__init__()
        self.parent = parent
        self.process = process
        self.source = source
        self.signals = ActionSignals()
        self.destination = destination
        self._id = str(uuid.uuid4())

    def run(self):
        self.signals.started.emit()
        con = QSqlDatabase.addDatabase('QSQLITE', self._id)
        con.setDatabaseName(settings.DATABASE)
        if not con.open():
            raise exceptions.DatabaseClosedException
        parent_type = self.parent.type
        destination_type = self.destination.type
        processed = 0
        # TODO: This is entirely duplicated from FoldersRunnable
        for root, dirs, files in self.source.walk():
            destination = os.path.abspath(
                os.path.join(
                    self.destination.root,
                    os.path.relpath(root.root, start=self.parent.root)
                )
            )
            # destination = self.destination.clean(destination)
            batch_size = 1
            output = []
            for f_item in files:
                if batch_size % 100 == 0:
                    if database.add_transfers(
                        items=output,
                        destination=destination,
                        s_type=parent_type,
                        d_type=destination_type,
                        con_name=self._id
                    ):
                        self.signals.select.emit()
                        if self.process:
                            self.signals.process_queue.emit()
                    else:
                        self.signals.error.emit('ERROR')
                    output = []
                # TODO: Is f_item not a fully fledged item?
                #       Why does it need to be created?
                print('here')
                '''
                if parent_type == 'local':
                    fname = os.path.join(
                        root.root, os.path.split(f_item.root)[1]
                    )
                    serialized_item = items.LocalItem(
                        fname, size=os.stat(fname).st_size
                    )
                elif parent_type == 's3':
                    fname = f'{root.root}{f_item.root.split("/")[-1]}'
                    serialized_item = f_item.create(
                        fname, size=f_item.size
                    )
                else:
                    raise Exception
                output.append(serialized_item)
                '''
                output.append(f_item)
                batch_size += 1
            if output:
                if database.add_transfers(
                    items=output,
                    destination=destination,
                    s_type=parent_type,
                    d_type=destination_type,
                    con_name=self._id
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
            f'Testing - {self.parent.root} - FOLDERS - FINISHED'
        )
        con.close()

    def __del__(self, *args, **kwargs):
        QSqlDatabase.removeDatabase(self._id)


class FoldersRunnable(BaseRunnable):

    def __init__(self, parent, folders, destination, process=False):
        super().__init__()
        self.process = process
        self.signals = ActionSignals()
        self.parent = parent
        self.folders = folders
        self.destination = destination
        self._id = str(uuid.uuid4())

    def run(self):
        # If Copy, a caught start will start the queue processing
        # May have to re-emit start to prevent deadlocks
        self.signals.started.emit()
        con = QSqlDatabase.addDatabase('QSQLITE', self._id)
        con.setDatabaseName(settings.DATABASE)
        if not con.open():
            raise exceptions.DatabaseClosedException
        parent_type = self.parent.type
        destination_type = self.destination.type
        for root_item in self.folders:
            processed = 0
            for root, dirs, files in root_item.walk():
                destination = os.path.abspath(
                    os.path.join(
                        self.destination.root,
                        os.path.relpath(root.root, start=self.parent.root)
                    )
                )
                # destination = self.destination.clean(destination)
                batch_size = 1
                output = []
                for f_item in files:
                    if batch_size % 100 == 0:
                        if database.add_transfers(
                            items=output,
                            destination=destination,
                            s_type=parent_type,
                            d_type=destination_type,
                            con_name=self._id
                        ):
                            self.signals.select.emit()
                            if self.process:
                                self.signals.process_queue.emit()
                        else:
                            self.signals.error.emit('ERROR')
                        output = []
                    if parent_type == 'local':
                        fname = os.path.join(
                            root.root, os.path.split(f_item.root)[1]
                        )
                        # TODO: This will be an f_item as well
                        serialized_item = items.LocalItem(
                            fname, size=os.stat(fname).st_size
                        )
                    elif parent_type == 's3':
                        fname = f'{root.root}{f_item.root.split("/")[-1]}'
                        serialized_item = f_item.create(
                            fname, size=f_item.size
                        )
                    else:
                        raise Exception
                    output.append(serialized_item)
                    batch_size += 1
                if output:
                    if database.add_transfers(
                        items=output,
                        destination=destination,
                        s_type=parent_type,
                        d_type=destination_type,
                        con_name=self._id
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
            f'Testing - {self.parent.root} - FOLDERS - FINISHED'
        )
        con.close()

    def __del__(self, *args, **kwargs):
        QSqlDatabase.removeDatabase(self._id)


class MixedItemsRunnable(BaseRunnable):

    def __init__(self, parent, files, folders, destination, process=False):
        super().__init__()
        self.process = process
        self.signals = ActionSignals()
        self.parent = parent
        self.files = files
        self.folders = folders
        self.destination = destination
        self._id = str(uuid.uuid4())

    @Slot()
    def run(self):
        # If Copy, a caught start will start the queue processing
        # May have to re-emit start to prevent deadlocks
        self.signals.started.emit()
        if self.process:
            self.signals.process_queue.emit()
        con = QSqlDatabase.addDatabase('QSQLITE', self._id)
        con.setDatabaseName(settings.DATABASE)
        if not con.open():
            raise exceptions.DatabaseClosedException
        database.add_transfers(
            items=self.files,
            destination=self.destination.root,
            s_type=self.parent.type,
            d_type=self.destination.type,
            con_name=self._id
        )
        self.signals.select.emit()
        if self.process:
            self.signals.process_queue.emit()
        for root_item in self.folders:
            processed = 0
            # for root, dirs, files in os.walk(root_item.root):
            for root, dirs, files in self.parent.walk(root_item.root):
                destination = os.path.abspath(
                    os.path.join(
                        self.destination,
                        os.path.relpath(root, start=self.parent.root)
                    )
                )
                batch_size = 1
                output = []
                for f in files:
                    if batch_size % 100 == 0:
                        if database.add_transfers(
                            items=output,
                            destination=destination,
                            s_type=self.parent.type,
                            d_type=self.destination.type,
                            con_name=self._id
                        ):
                            self.signals.select.emit()
                            if self.process:
                                self.signals.process_queue.emit()
                        else:
                            self.signals.error.emit('ERROR')
                        output = []
                    fname = os.path.join(root, f)
                    if os.path.isfile(fname):
                        serialized_item = items.LocalItem(
                            fname, size=os.stat(fname).st_size
                        )
                        output.append(serialized_item)
                        batch_size += 1
                if output:
                    if database.add_transfers(
                        items=output,
                        destination=destination,
                        s_type=self.parent.type,
                        d_type=self.destination.type,
                        con_name=self._id
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
        self.signals.finished.emit(f'Testing - {self.parent.root} - FINISHED')
        con.close()

    def __del__(self, *args, **kwargs):
        QSqlDatabase.removeDatabase(self._id)


class FilesRunnable(BaseRunnable):

    def __init__(self, parent, files, destination, process=False):
        super().__init__()
        self.process = process
        self.signals = ActionSignals()
        self.parent = parent
        self.files = files
        self.destination = destination
        self._id = str(uuid.uuid4())

    @Slot()
    def run(self):
        self.signals.started.emit()
        if self.process:
            self.signals.process_queue.emit()
        con = QSqlDatabase.addDatabase('QSQLITE', self._id)
        con.setDatabaseName(settings.DATABASE)
        if not con.open():
            raise exceptions.DatabaseClosedException
        database.add_transfers(
            items=self.files,
            destination=self.destination.root,
            s_type=self.parent.type,
            d_type=self.destination.type,
            con_name=self._id,
        )
        self.signals.select.emit()
        self.signals.finished.emit(f'Testing - {self.parent.root} - FINISHED')
        con.close()

    def __del__(self, *args, **kwargs):
        QSqlDatabase.removeDatabase(self._id)


class RemoveItemsRunnable(BaseRunnable):

    def __init__(self, parent, items):
        super().__init__()
        self.items = items
        self.signals = ActionSignals()
        self.parent = parent
        self._id = str(uuid.uuid4())

    @Slot()
    def run(self):
        self.signals.started.emit()
        func = self.parent.model().remove_rows
        deleted_items = []
        for index, item in enumerate(self.items, start=1):
            item.remove()
            deleted_items.append(item)
            if index % 10 == 0:
                self.signals.callback.emit(partial(func, deleted_items))
                deleted_items = []
        if deleted_items:
            self.signals.callback.emit(partial(func, deleted_items))
        self.signals.finished.emit(f'Testing - {self.parent.root} - FINISHED')
