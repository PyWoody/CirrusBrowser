import os
import uuid

from functools import partial

from .base import BaseAction, BaseRunnable
from cirrus import database, dialogs, items, settings, utils
from cirrus.actions.signals import ActionSignals
from cirrus.windows.search import SearchResultsWindow

from PySide6.QtCore import Slot
from PySide6.QtGui import QIcon


class SearchAction(BaseAction):

    def __init__(self, parent, folders=None):
        super().__init__(parent)
        self.dialog = None
        self.parent = parent
        self.folders = folders
        self.setIcon(QIcon(os.path.join(settings.ICON_DIR, 'search.svg')))
        self.setText('Search')
        self.setStatusTip(
            'Advanced controls for filtering with additional options'
        )

    def show_dialog(self):
        self.dialog = dialogs.SearchItemsDialog(
            parent=self.parent, folders=self.folders
        )
        self.dialog.accepted.connect(self.accepted.emit)
        self.dialog.setModal(True)
        self.dialog.show()
        return True

    def runnable(self):
        return SearchRunnable(self.parent, self.dialog)


class TransferFilterAction(BaseAction):

    def __init__(self, parent, folders=None):
        super().__init__(parent)
        self.dialog = None
        self.parent = parent
        self.folders = folders
        self.setText('Filter (Advanced)')
        self.setStatusTip(
            'Advanced controls for filtering with additional options'
        )

    def show_dialog(self):
        self.dialog = dialogs.SearchItemsDialog(
            parent=self.parent, folders=self.folders
        )
        self.dialog.accepted.connect(self.accepted.emit)
        self.dialog.setModal(True)
        self.dialog.show()
        return True

    def runnable(self):
        return TransferFilterRunnable(self.parent, self.dialog)


class SearchRunnable(BaseRunnable):

    def __init__(self, parent, dialog, process=False):
        super().__init__()
        self.setAutoDelete(False)
        self.parent = parent
        self.dialog = dialog
        self.signals = ActionSignals()
        self.search_results_window = SearchResultsWindow(self.dialog.folders)
        self.signals.finished.connect(
            self.search_results_window.search_completed
        )
        self.search_results_window.aborted.connect(self.stop)
        self.search_results_window.closed.connect(self.closed)
        self.search_results_window.show()
        self._id = str(uuid.uuid4())
        self.stopped = False

    @Slot()
    def run(self):
        self.signals.started.emit()
        filters = []
        if name := self.dialog.name.text():
            name = os.path.splitext(name)[0]
            filters.append(
                partial(
                    self.dialog.name_option.itemData(
                        self.dialog.name_option.currentIndex()
                    ),
                    name
                )
            )
        if file_type := self.dialog.file_types.text():
            file_type = '.' + file_type.lstrip('.')
            filters.append(
                partial(
                    self.dialog.file_types_option.itemData(
                        self.dialog.file_types_option.currentIndex()
                    ),
                    file_type
                )
            )
        if ctime := self.dialog.ctime.text():
            if str(ctime) != '0':
                value_text = self.dialog.ctime_option_increment.currentText()
                compare_date = utils.date.subtract_period(value_text, ctime)
                seconds = utils.date.period_to_seconds(value_text, ctime)
                filters.append(
                    partial(
                        self.dialog.ctime_option.itemData(
                            self.dialog.ctime_option.currentIndex()
                        ),
                        compare_date,
                        seconds
                    )
                )
        if mtime := self.dialog.mtime.text():
            if str(mtime) != '0':
                value_text = self.dialog.mtime_option_increment.currentText()
                compare_date = utils.date.subtract_period(value_text, mtime)
                seconds = utils.date.period_to_seconds(value_text, mtime)
                filters.append(
                    partial(
                        self.dialog.mtime_option.itemData(
                            self.dialog.mtime_option.currentIndex()
                        ),
                        compare_date,
                        seconds
                    )
                )
        if (size := self.dialog.size.text()) != '0':
            value = self.dialog.size_option_increment.currentText()
            value = utils.files.human_to_bytes(f'{size}{value}')
            filters.append(
                partial(
                    self.dialog.size_option.itemData(
                        self.dialog.size_option.currentIndex()
                    ),
                    value
                )
            )
        cb_func = self.search_results_window.view.model().add_result
        if self.dialog.recursive:
            search_func = self.recursive_search
        else:
            search_func = self.top_level_search
        for folder in self.dialog.folders:
            if self.stopped:
                self.signals.finished.emit('Stopped')
                self.signals.aborted.emit()
                return
            # TODO: Bulk updates
            for result in search_func(folder):
                if self.stopped:
                    self.signals.finished.emit('Stopped')
                    self.signals.aborted.emit()
                    return
                if all(f(result) for f in filters):
                    self.signals.callback.emit(partial(cb_func, result))
        self.signals.finished.emit('Completed')

    def recursive_search(self, item):
        for root, dirs, files in item.walk():
            yield from dirs
            yield from files

    def top_level_search(self, item):
        yield from item.listdir()

    def stop(self):
        self.stopped = True

    @Slot()
    def closed(self):
        # Probably redundant but good practice to ensure GC
        self.stopped = True
        self.parent = None
        self = None


class TransferFilterRunnable(BaseRunnable):

    def __init__(self, parent, dialog, process=False):
        super().__init__()
        self.setAutoDelete(False)
        self.parent = parent
        self.dialog = dialog
        self.signals = ActionSignals()
        self._id = str(uuid.uuid4())

    @Slot()
    def run(self):
        self.signals.started.emit()
        filters = []
        if name := self.dialog.name.text():
            name = os.path.splitext(name)[0]
            filters.append(
                partial(
                    self.dialog.name_option.itemData(
                        self.dialog.name_option.currentIndex()
                    ),
                    name
                )
            )
        if file_type := self.dialog.file_types.text():
            file_type = '.' + file_type.lstrip('.')
            filters.append(
                partial(
                    self.dialog.file_types_option.itemData(
                        self.dialog.file_types_option.currentIndex()
                    ),
                    file_type
                )
            )
        if ctime := self.dialog.ctime.text():
            if str(ctime) != '0':
                value_text = self.dialog.ctime_option_increment.currentText()
                compare_date = utils.date.subtract_period(value_text, ctime)
                seconds = utils.date.period_to_seconds(value_text, ctime)
                filters.append(
                    partial(
                        self.dialog.ctime_option.itemData(
                            self.dialog.ctime_option.currentIndex()
                        ),
                        compare_date,
                        seconds
                    )
                )
        if mtime := self.dialog.mtime.text():
            if str(mtime) != '0':
                value_text = self.dialog.mtime_option_increment.currentText()
                compare_date = utils.date.subtract_period(value_text, mtime)
                seconds = utils.date.period_to_seconds(value_text, mtime)
                filters.append(
                    partial(
                        self.dialog.mtime_option.itemData(
                            self.dialog.mtime_option.currentIndex()
                        ),
                        compare_date,
                        seconds
                    )
                )
        if (size := self.dialog.size.text()) != '0':
            value_text = self.dialog.size_option_increment.currentText()
            value = utils.files.human_to_bytes(f'{size}{value_text}')
            filters.append(
                partial(
                    self.dialog.size_option.itemData(
                        self.dialog.size_option.currentIndex()
                    ),
                    value
                )
            )
        if self.dialog.recursive:
            search_func = self.recursive_search
        else:
            search_func = self.top_level_search
        batch_size = 1
        output = []
        for folder in self.dialog.folders:
            for result in search_func(folder):
                if result.is_dir:
                    continue
                # TODO: Make this an `any` generator
                for _filter in filters:
                    if not _filter.func(result, *_filter.args):
                        break
                else:
                    destination = os.path.abspath(
                        os.path.join(
                            self.destination.root,
                            os.path.relpath(
                                os.path.dirname(result.root),
                                start=self.parent.root
                            )
                        )
                    )
                    # TODO: This was halfway re-worked
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
        self.signals.finished.emit(f'Testing - {self.parent.root} - FINISHED')

    def recursive_search(self, item):
        for root, dirs, files in item.walk():
            yield from dirs
            yield from files

    def top_level_search(self, item):
        yield from item.listdir()

    @Slot()
    def closed(self):
        # Probably redundant but good practice to ensure GC
        self.parent = None
        self = None
