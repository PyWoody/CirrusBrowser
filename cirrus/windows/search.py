from functools import partial

from cirrus.models import SearchResultsModel
from cirrus.views.search import SearchResultsTreeView

from PySide6.QtCore import Qt, Slot, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class SearchResultsWindow(QWidget):
    aborted = Signal()
    closed = Signal()

    def __init__(self):
        super().__init__()
        self.resize(725, 475)
        self.setWindowTitle('Searching...')
        model = SearchResultsModel()
        self.view = SearchResultsTreeView()
        self.view.setModel(model)
        self.view.setup_header()
        self.view.checked.connect(self.enable_btns)
        self.view.all_unchecked.connect(self.disable_btns)

        # TODO: Button left-aligned: Select All
        #       Can't be done with button box. Will have to do QHBoxLayout
        #       w/ spacer
        button_layout = QHBoxLayout()
        self.select_all_btn = QPushButton('Select All')
        self.select_all_btn.clicked.connect(self.select_all)
        self.select_all_btn.setEnabled(False)
        self.clear_selection_btn = QPushButton('Clear Selection')
        self.clear_selection_btn.clicked.connect(self.clear_selection)
        self.clear_selection_btn.setEnabled(False)
        self.stop_btn = QPushButton('&Stop')
        self.delete_btn = QPushButton('Delete')
        self.delete_btn.setEnabled(False)
        self.download_btn = QPushButton('Download')
        self.download_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.aborted.emit)
        self.stop_btn.clicked.connect(partial(self.stop_btn.setEnabled, False))
        button_layout.addWidget(self.select_all_btn)
        button_layout.addWidget(self.clear_selection_btn)
        button_layout.addStretch(1)
        button_layout.addWidget(self.download_btn)
        button_layout.addWidget(self.delete_btn)
        button_layout.addWidget(self.stop_btn)

        layout = QVBoxLayout()
        layout.addWidget(self.view)
        layout.addLayout(button_layout)
        self.setLayout(layout)

    def closeEvent(self, event):
        self.closed.emit()
        super().closeEvent(event)

    @Slot(str)
    def search_completed(self, msg):
        self.stop_btn.setEnabled(False)
        self.select_all_btn.setEnabled(True)
        if msg in {'Stopped', 'Aborted', 'Completed'}:
            self.setWindowTitle(f'Search Results - {msg}')
        else:
            self.setWindowTitle('Search Results')

    @Slot()
    def clear_selection(self):
        if (index := self.view.model().index(0, 0)).isValid():
            top_left = None
            bottom_right = None
            for checkbox in self.view.model().match(
                index,
                Qt.DisplayRole,
                Qt.Checked,
                flags=Qt.MatchExactly,
                hits=-1,
            ):
                self.view.model().setData(checkbox, Qt.Unchecked)
                if top_left is None:
                    top_left = checkbox
                elif top_left.row() > checkbox.row():
                    top_left = checkbox
                if bottom_right is None:
                    bottom_right = checkbox
                elif bottom_right.row() < checkbox.row():
                    bottom_right = checkbox
            self.view.model().dataChanged.emit(top_left, bottom_right)
            self.clear_selection_btn.setEnabled(False)
            if not self.select_all_btn.isEnabled():
                self.select_all_btn.setEnabled(True)

    @Slot()
    def select_all(self):
        if (index := self.view.model().index(0, 0)).isValid():
            top_left = None
            bottom_right = None
            for checkbox in self.view.model().match(
                index,
                Qt.DisplayRole,
                Qt.Unchecked,
                flags=Qt.MatchExactly,
                hits=-1,
            ):
                self.view.model().setData(checkbox, Qt.Checked)
                if top_left is None:
                    top_left = checkbox
                elif top_left.row() > checkbox.row():
                    top_left = checkbox
                if bottom_right is None:
                    bottom_right = checkbox
                elif bottom_right.row() < checkbox.row():
                    bottom_right = checkbox
            for checkbox in self.view.model().match(
                index,
                Qt.DisplayRole,
                '0',
                flags=Qt.MatchExactly,
                hits=-1,
            ):
                self.view.model().setData(checkbox, Qt.Checked)
                if top_left is None:
                    top_left = checkbox
                elif top_left.row() > checkbox.row():
                    top_left = checkbox
                if bottom_right is None:
                    bottom_right = checkbox
                elif bottom_right.row() < checkbox.row():
                    bottom_right = checkbox
            self.view.model().dataChanged.emit(top_left, bottom_right)
            if not self.clear_selection_btn.isEnabled():
                self.clear_selection_btn.setEnabled(True)

    @Slot()
    def enable_btns(self):
        if not self.delete_btn.isEnabled():
            self.delete_btn.setEnabled(True)
        if not self.download_btn.isEnabled():
            self.download_btn.setEnabled(True)
        if not self.clear_selection_btn.isEnabled():
            self.clear_selection_btn.setEnabled(True)

    @Slot()
    def disable_btns(self):
        if self.delete_btn.isEnabled():
            self.delete_btn.setEnabled(False)
        if self.download_btn.isEnabled():
            self.download_btn.setEnabled(False)
        if self.clear_selection_btn.isEnabled():
            self.clear_selection_btn.setEnabled(False)
