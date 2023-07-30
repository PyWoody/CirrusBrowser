import os

from functools import partial

from .base import BaseAction, BaseRunnable
from cirrus import database, dialogs, items, settings, utils
from cirrus.actions.signals import ActionSignals

from PySide6.QtCore import Slot
from PySide6.QtGui import QIcon


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


class CopyRecursiveItemsAction(BaseAction):

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
        return RecursiveAddItemsRunnable(
            self.parent,
            files=self.files,
            folders=self.folders,
            destination=self.destination,
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
        return RecursiveAddItemsRunnable(
            self.parent,
            folder=self.source,
            destination=self.destination,
            process=True,
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
        return RecursiveAddItemsRunnable(
            self.parent,
            folders=self.folders,
            destination=self.destination,
            process=True,
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
        return RecursiveAddItemsRunnable(
            self.parent,
            folder=self.source,
            destination=self.destination,
        )


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
        return RecursiveAddItemsRunnable(
            self.parent,
            folders=self.folders,
            destination=self.destination,
        )


class QueueRecursiveItemsAction(BaseAction):

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
        return RecursiveAddItemsRunnable(
            self.parent,
            files=self.files,
            folders=self.folders,
            destination=self.destination,
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
                client = items.new_client(self.parent.client, path)
                item(client, is_dir=True).makedirs()
        self.signals.finished.emit(f'Testing - {self.parent.root} - FINISHED')
        self.signals.callback.emit(self.parent.refresh)


class RecursiveAddItemsRunnable(BaseRunnable):

    def __init__(
        self,
        parent,
        *,
        destination,
        folder=None,
        folders=None,
        files=None,
        process=False
    ):
        super().__init__()
        self.process = process
        self.signals = ActionSignals()
        self.parent = parent
        self.files = files
        self.folders = []
        if folder is not None:
            self.folders.append(folder)
        if folders is not None:
            self.folders.extend(folders)
        self.destination = destination

    @Slot()
    def run(self):
        # If Copy, a caught start will start the queue processing
        # May have to re-emit start to prevent deadlocks
        self.signals.started.emit()
        if self.process:
            self.signals.process_queue.emit()
        if self.files is not None:
            cb = partial(
                database.add_transfers,
                items=self.files,
                destination=self.destination.root,
                s_type=self.parent.type,
                d_type=self.destination.type,
            )
            self.signals.callback.emit(cb)
            self.signals.select.emit()
            if self.process:
                self.signals.process_queue.emit()
        for folder in self.folders:
            processed = 0
            for root, dirs, files in folder.walk():
                destination = os.path.abspath(
                    os.path.join(
                        self.destination.root,
                        os.path.basename(folder.root.rstrip('/')),
                        os.path.relpath(root.root, start=folder.root)
                    )
                )
                batch_size = 1
                output = []
                for f in files:
                    if batch_size % 1_000 == 0:
                        cb = partial(
                            database.add_transfers,
                            items=output,
                            destination=destination,
                            s_type=self.parent.type,
                            d_type=self.destination.type,
                        )
                        self.signals.callback.emit(cb)
                        self.signals.select.emit()
                        if self.process:
                            self.signals.process_queue.emit()
                        output = []
                    output.append(f)
                    batch_size += 1
                processed += batch_size - 1
            if processed:
                self.signals.update.emit(f'Added {processed:,} to queue.')
        if output:
            cb = partial(
                database.add_transfers,
                items=output,
                destination=destination,
                s_type=self.parent.type,
                d_type=self.destination.type,
            )
            self.signals.callback.emit(cb)
            self.signals.select.emit()
            if self.process:
                self.signals.process_queue.emit()
        if processed:
            self.signals.update.emit(
                f'{processed:,} items were added to the queue.'
            )
        self.signals.select.emit()
        if self.process:
            self.signals.process_queue.emit()
        self.signals.finished.emit(f'Testing - {self.parent.root} - FINISHED')


class FilesRunnable(BaseRunnable):

    def __init__(self, parent, files, destination, process=False):
        super().__init__()
        self.process = process
        self.signals = ActionSignals()
        self.parent = parent
        self.files = files
        self.destination = destination

    @Slot()
    def run(self):
        self.signals.started.emit()
        if self.process:
            self.signals.process_queue.emit()
        cb = partial(
            database.add_transfers,
            items=self.files,
            destination=self.destination.root,
            s_type=self.parent.type,
            d_type=self.destination.type,
        )
        self.signals.callback.emit(cb)
        self.signals.select.emit()
        self.signals.finished.emit(f'Testing - {self.parent.root} - FINISHED')


class RemoveItemsRunnable(BaseRunnable):

    def __init__(self, parent, items):
        super().__init__()
        self.items = items
        self.signals = ActionSignals()
        self.parent = parent

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
