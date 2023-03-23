
from cirrus.models import SearchResultsModel
from cirrus.views.search import SearchResultsTreeView

from PySide6.QtCore import QItemSelection, Slot, Signal
from PySide6.QtWidgets import (
    QMainWindow,
    QVBoxLayout,
    QWidget,
)


class SearchResultsWindow(QMainWindow):
    closed = Signal()

    def __init__(self):
        super().__init__()
        self.resize(725, 475)
        model = SearchResultsModel()
        self.view = SearchResultsTreeView()
        self.view.setModel(model)
        self.view.setup_header()
        widget = QWidget()
        layout = QVBoxLayout()
        layout.addWidget(self.view)
        widget.setLayout(layout)
        self.setCentralWidget(widget)

    def closeEvent(self, event):
        self.closed.emit()
        super().closeEvent(event)

    @Slot(QItemSelection, QItemSelection)
    def selectionChanged(self, selected, deselected):
        pass
