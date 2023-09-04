import os

from functools import partial

from .base import BaseAction, BaseRunnable
from cirrus import dialogs, settings, utils
from cirrus.actions.signals import ActionSignals
from cirrus.windows.search import SearchResultsWindow

from PySide6.QtCore import Slot
from PySide6.QtGui import QIcon


class SearchAllAction(BaseAction):

    def __init__(self, parent, folders=None):
        super().__init__(parent)
        self.dialog = None
        self.parent = parent
        self.folders = folders
        self.setIcon(QIcon(os.path.join(settings.ICON_DIR, 'search.svg')))
        self.setText('Search All')
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


class SearchByPanelAction(BaseAction):

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


class SearchRunnable(BaseRunnable):

    def __init__(self, parent, dialog, process=False):
        super().__init__()
        self.setAutoDelete(False)
        self.parent = parent
        self.dialog = dialog
        self.signals = ActionSignals()
        self.search_results_window = SearchResultsWindow(
            self.dialog.location_selections
        )
        self.signals.finished.connect(
            self.search_results_window.search_completed
        )
        self.search_results_window.aborted.connect(self.stop)
        self.search_results_window.closed.connect(self.closed)
        self.search_results_window.show()
        self.stopped = False

    @Slot()
    def run(self):
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
                value_text = self.dialog.filters.ctime_option_increment.currentText()  # noqa E501
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
                value_text = self.dialog.filters.mtime_option_increment.currentText()  # noqa E501
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
            value = self.dialog.filters.size_option_increment.currentText()
            value = utils.files.human_to_bytes(f'{size}{value}')
            filters.append(
                partial(
                    self.dialog.filters.size_option.itemData(
                        self.dialog.filters.size_option.currentIndex()
                    ),
                    value
                )
            )
        cb_func = self.search_results_window.view.model().add_results
        if self.dialog.recursive:
            search_func = self.recursive_search
        else:
            search_func = self.top_level_search
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
        results = []
        for folder in search_folders:
            if self.stopped:
                self.signals.finished.emit('Stopped')
                self.signals.aborted.emit()
                return
            for result in search_func(folder):
                if self.stopped:
                    self.signals.finished.emit('Stopped')
                    self.signals.aborted.emit()
                    return
                if all(f(result) for f in filters):
                    results.append(result)
                    if len(results) % 100 == 0:
                        self.signals.callback.emit(partial(cb_func, results))
                        results = []
        if results:
            self.signals.callback.emit(partial(cb_func, results))
        self.signals.finished.emit('Completed')

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
