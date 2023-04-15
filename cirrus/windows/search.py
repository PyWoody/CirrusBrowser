from functools import partial

from cirrus.models import SearchResultsModel
from cirrus.views.search import SearchResultsTreeView

from PySide6.QtCore import Slot, Signal
from PySide6.QtWidgets import (
    QDialogButtonBox,
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

        button_box = QDialogButtonBox()
        self.stop_btn = button_box.addButton(
            '&Stop', QDialogButtonBox.ButtonRole.RejectRole
        )
        self.delete_btn = button_box.addButton(
            'Delete', QDialogButtonBox.ButtonRole.ActionRole
        )
        self.delete_btn.setEnabled(False)
        self.download_btn = button_box.addButton(
            'Download', QDialogButtonBox.ButtonRole.ActionRole
        )
        self.download_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.aborted.emit)
        button_box.rejected.connect(partial(self.stop_btn.setEnabled, False))

        layout = QVBoxLayout()
        layout.addWidget(self.view)
        layout.addWidget(button_box)
        self.setLayout(layout)

    def closeEvent(self, event):
        self.closed.emit()
        super().closeEvent(event)

    @Slot(str)
    def search_completed(self, msg):
        self.stop_btn.setEnabled(False)
        if msg in {'Stopped', 'Aborted', 'Completed'}:
            self.setWindowTitle(f'Search Results - {msg}')
        else:
            self.setWindowTitle('Search Results')

    @Slot()
    def enable_btns(self):
        if not self.delete_btn.isEnabled():
            self.delete_btn.setEnabled(True)
        if not self.download_btn.isEnabled():
            self.download_btn.setEnabled(True)

    @Slot()
    def disable_btns(self):
        if self.delete_btn.isEnabled():
            self.delete_btn.setEnabled(False)
        if self.download_btn.isEnabled():
            self.download_btn.setEnabled(False)
