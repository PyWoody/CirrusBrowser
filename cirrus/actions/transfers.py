import os
import uuid

from functools import partial

from .base import BaseAction, BaseRunnable
from cirrus import database, dialogs, exceptions, items, settings, utils
from cirrus.actions.signals import ActionSignals

from PySide6.QtCore import Slot
from PySide6.QtSql import QSqlDatabase


class DropRowsAction(BaseAction):

    def __init__(self, parent, indexes):
        super().__init__(parent)
        self.parent = parent
        self.indexes = indexes
        self.setText('Remove selection')
        self.setStatusTip('Removes the selected rows from the database.')

    def runnable(self):
        return DropRowsRunnable(self.parent, self.indexes)


class DropRowsRunnable(BaseRunnable):

    def __init__(self, parent, indexes):
        super().__init__()
        self.parent = parent
        self.signals = ActionSignals()
        self.indexes = indexes

    def run(self):
        # TODO: Items could still be in the database.hot_queue
        # TODO: removeRows can take a count. Do in groups, else removeRow(
        prev_row = None
        row_group = []
        for index in self.indexes:
            if prev_row is None:
                prev_row = index.row()
                row_group.append(index)
            elif (prev_row + 1) == index.row():
                row_group.append(index)
            else:
                # Pending rows
                success = self.parent.model().removeRows(
                    row_group[0].row(), len(row_group)
                )
                if success:
                    for row in row_group:
                        self.signals.update.emit(
                            row.siblingAtColumn(1).data()
                        )
                else:
                    self.signals.error.emit(
                        f'Failed to drop rows {row_group[0].row()} to '
                        f'{row_group[-1].row()}'
                    )
                # Current row
                if self.parent.model().removeRow(index.row()):
                    self.signals.update.emit(index.siblingAtColumn(1).data())
                else:
                    self.signals.error.emit(f'Failed to drop row: {index.row()}')
                prev_row = None
                row_group = []
        if row_group:
            success = self.parent.model().removeRows(
                row_group[0].row(), len(row_group)
            )
            if success:
                for row in row_group:
                    self.signals.update.emit(
                        row.siblingAtColumn(1).data()
                    )
        self.signals.select.emit()
        self.signals.finished.emit('Finished drop')
        self.parent.model().submitAll()


class TransferFilterAction(BaseAction):

    def __init__(self, parent, *, destinations, folders=None):
        super().__init__(parent)
        self.dialog = None
        self.parent = parent
        self.destinations = list(destinations)
        self.folders = None if folders is None else list(folders)
        self.setText('Copy (Filter)')
        self.setStatusTip(
            'Advanced controls for filtering with additional options'
        )

    def show_dialog(self):
        self.dialog = dialogs.TransferItemsDialog(
            parent=self.parent,
            folders=self.folders,
            destinations=self.destinations,
        )
        self.dialog.accepted.connect(self.accepted.emit)
        self.dialog.setModal(True)
        self.dialog.show()
        return True

    def runnable(self):
        return TransferFilterRunnable(self.parent, self.dialog)


class TransferFilterRunnable(BaseRunnable):

    def __init__(self, parent, dialog, process=False):
        super().__init__()
        self.setAutoDelete(False)
        self.parent = parent
        self.dialog = dialog
        self.process = process
        self.signals = ActionSignals()
        self.stopped = False

    @Slot()
    def run(self):
        print(self.dialog.add_to_queue_radio.isChecked())
        print(self.dialog.add_and_start_radio.isChecked())
        print(self.dialog.folders)
        print(self.dialog.destinations)
        print(self.parent.type, self.parent.user)
        self.signals.started.emit()
        filters = []
        if name := self.dialog.filters.name.text():
            name = os.path.splitext(name)[0]
            filters.append(
                partial(
                    self.dialog.filters.name_option.itemData(
                        self.dialog.filters.name_option.currentIndex()
                    ),
                    name
                )
            )
        if file_type := self.dialog.filters.file_types.text():
            file_type = '.' + file_type.lstrip('.')
            filters.append(
                partial(
                    self.dialog.filters.file_types_option.itemData(
                        self.dialog.filters.file_types_option.currentIndex()
                    ),
                    file_type
                )
            )
        if ctime := self.dialog.filters.ctime.text():
            if str(ctime) != '0':
                value_text = self.dialog.filters.ctime_option_increment.currentText()
                compare_date = utils.date.subtract_period(value_text, ctime)
                seconds = utils.date.period_to_seconds(value_text, ctime)
                filters.append(
                    partial(
                        self.dialog.filters.ctime_option.itemData(
                            self.dialog.filters.ctime_option.currentIndex()
                        ),
                        compare_date,
                        seconds
                    )
                )
        if mtime := self.dialog.filters.mtime.text():
            if str(mtime) != '0':
                value_text = self.dialog.filters.mtime_option_increment.currentText()
                compare_date = utils.date.subtract_period(value_text, mtime)
                seconds = utils.date.period_to_seconds(value_text, mtime)
                filters.append(
                    partial(
                        self.dialog.filters.mtime_option.itemData(
                            self.dialog.filters.mtime_option.currentIndex()
                        ),
                        compare_date,
                        seconds
                    )
                )
        if (size := self.dialog.filters.size.text()) != '0':
            value_text = self.dialog.filters.size_option_increment.currentText()
            value = utils.files.human_to_bytes(f'{size}{value_text}')
            filters.append(
                partial(
                    self.dialog.filters.size_option.itemData(
                        self.dialog.filters.size_option.currentIndex()
                    ),
                    value
                )
            )
        if self.dialog.recursive:
            search_func = self.recursive_search
        else:
            search_func = self.top_level_search
        # Start Folders
        if len(self.dialog.folders) == 1:
            location_selections = {self.dialog.folders[0].root}
        else:
            location_selections = {
                i.text() for i in self.dialog.location_selections
                if i.isChecked()
            }
        search_folders = (
            i for i in self.dialog.folders if i.root in location_selections
        )
        # Destination Folders
        if len(self.dialog.destinations) == 1:
            dest_location_selections = {self.dialog.destinations[0].root}
        else:
            dest_location_selections = {
                i.text() for i in self.dialog.destination_selections
                if i.isChecked()
            }
        destination_folders = [
            i for i
            in self.dialog.destinations if i.root in dest_location_selections
        ]
        batch_size = 1
        output = []
        for folder in search_folders:
            if self.stopped:
                # TODO: Push to the DB anything pending
                self.signals.finished.emit('Stopped')
                self.signals.aborted.emit()
                return
            for result in search_func(folder):
                if self.stopped:
                    # TODO: Push to the DB anything pending
                    self.signals.finished.emit('Stopped')
                    self.signals.aborted.emit()
                    return
                if all(f(result) for f in filters):
                    for destination in destination_folders:
                        dest = os.path.abspath(
                            os.path.join(
                                destination.root,
                                os.path.relpath(
                                    result.root,
                                    # start=self.parent.root
                                    start=folder.root
                                )
                            )
                        )
                        print('DEST:', dest)
                    '''
                    # TODO: This was halfway re-worked
                    if batch_size % 100 == 0:
                        if database.add_transfers(
                            items=output,
                            destination=destination,
                            s_type=parent_type,
                            d_type=destination_type,
                        ):
                            self.signals.select.emit()
                            if self.process:
                                self.signals.process_queue.emit()
                        else:
                            self.signals.error.emit('ERROR')
                        output = []
                    if parent_type == 'local':
                        serialized_item = items.LocalItem(
                            result.root, size=os.stat(result.root).st_size
                        )
                    elif parent_type == 's3':
                        fname = f'{self.root}{result.root.split("/")[-1]}'
                        serialized_item = result.create(
                            fname, size=result.size
                        )
                    else:
                        raise Exception
                    output.append(serialized_item)
                    batch_size += 1
                    '''
        self.signals.finished.emit(f'Testing - {self.parent.root} - FINISHED')

    def recursive_search(self, item):
        for _, __, files in item.walk():
            yield from files

    def top_level_search(self, item):
        for result in item.listdir():
            if not result.is_dir:
                yield result

    def stop(self):
        self.stopped = True

    @Slot()
    def closed(self):
        # Probably redundant but good practice to ensure GC
        self.stopped = True
        self.parent = None
        self = None
