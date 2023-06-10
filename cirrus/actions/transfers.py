import os

from collections import defaultdict
from functools import partial

from .base import BaseAction, BaseRunnable
from cirrus import database, dialogs, utils
from cirrus.actions.signals import ActionSignals

from PySide6.QtCore import Slot


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
        self.setAutoDelete(False)
        self.parent = parent
        self.signals = ActionSignals()
        self.indexes = indexes

    def run(self):
        # TODO: Items could still be in the database.hot_queue
        self.parent.clearSelection()
        model = self.parent.model()
        for index in self.indexes:
            self.signals.ss_callback.emit(
                partial(model.removeRow, index.row())
            )
        self.signals.ss_callback.emit(self.signals.select.emit)

class TransferFilterAction(BaseAction):

    def __init__(self, parent, *, destinations, folders=None):
        super().__init__(parent)
        self.dialog = None
        self.parent = parent
        self.destinations = list(destinations)
        self.folders = None if folders is None else list(folders)
        self.setText('Advanced')
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

    def __init__(self, parent, dialog):
        super().__init__()
        self.setAutoDelete(False)
        self.parent = parent
        self.dialog = dialog
        self.signals = ActionSignals()
        self.stopped = False

    @Slot()
    def run(self):
        self.process = self.dialog.add_and_start_radio.isChecked()
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
        destinations = [
            i for i in self.dialog.destinations
            if i.root in dest_location_selections
        ]
        for folder in search_folders:
            batch_size = 1
            processed = 0
            output = defaultdict(list)
            if self.stopped:
                if output:
                    for dest, queued_items in output.items():
                        cb = partial(
                            database.add_transfers,
                            items=queued_items,
                            destination=dest.root,
                            s_type=folder.type,
                            d_type=dest.type,
                        )
                        self.signals.callback.emit(cb)
                    self.signals.select.emit()
                    if self.process:
                        self.signals.process_queue.emit()
                self.signals.finished.emit('Stopped')
                self.signals.aborted.emit()
                return
            for result in search_func(folder):
                if self.stopped:
                    if output:
                        for dest, queued_items in output.items():
                            cb = partial(
                                database.add_transfers,
                                items=queued_items,
                                destination=dest.root,
                                s_type=folder.type,
                                d_type=dest.type,
                            )
                            self.signals.callback.emit(cb)
                        self.signals.select.emit()
                        if self.process:
                            self.signals.process_queue.emit()
                    self.signals.finished.emit('Stopped')
                    self.signals.aborted.emit()
                    return
                if all(f(result) for f in filters):
                    for destination in destinations:
                        if batch_size % 100 == 0:
                            for dst_root_type, queued_items in output.items():
                                cb = partial(
                                    database.add_transfers,
                                    items=queued_items,
                                    destination=dst_root_type[0],
                                    s_type=folder.type,
                                    d_type=dst_root_type[1],
                                )
                                self.signals.callback.emit(cb)
                            self.signals.select.emit()
                            if self.process:
                                self.signals.process_queue.emit()
                            output = defaultdict(list)
                        dst_path = os.path.dirname(
                            os.path.abspath(
                                os.path.join(
                                    destination.root,
                                    os.path.basename(folder.root.rstrip('/')),
                                    os.path.relpath(
                                        result.root,
                                        start=folder.root
                                    )
                                )
                            )
                        )
                        output[(dst_path, destination.type)].append(result)
                        batch_size += 1
                if output:
                    for dst_root_type, queued_items in output.items():
                        cb = partial(
                            database.add_transfers,
                            items=queued_items,
                            destination=dst_root_type[0],
                            s_type=folder.type,
                            d_type=dst_root_type[1],
                        )
                        self.signals.callback.emit(cb)
                    self.signals.select.emit()
                    if self.process:
                        self.signals.process_queue.emit()
                    output = defaultdict(list)
            processed += batch_size - 1
            if processed:
                self.signals.update.emit(f'Added {processed:,} to queue.')
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
