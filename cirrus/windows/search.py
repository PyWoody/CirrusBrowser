from functools import partial

from cirrus.models import SearchResultsModel
from cirrus.views.search import SearchResultsTreeView
from cirrus.widgets import FlowLayout

from PySide6.QtCore import Qt, QItemSelectionModel, QModelIndex, Slot, Signal
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QToolButton,
    QWidget,
)


class SearchResultsWindow(QWidget):
    aborted = Signal()
    closed = Signal()

    def __init__(self, labels):
        super().__init__()
        self.resize(725, 475)
        self.setWindowTitle('Searching...')
        model = SearchResultsModel()
        self.view = SearchResultsTreeView()
        self.view.setModel(model)
        self.view.setup_header()
        self.view.checked.connect(self.enable_action_btns)
        self.view.unchecked.connect(self.unchecked)
        self.view.all_unchecked.connect(self.disable_action_btns)
        self.view.all_checked.connect(self.all_checked)

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
        self.download_btn.clicked.connect(self.download)
        self.stop_btn.clicked.connect(self.aborted.emit)
        self.stop_btn.clicked.connect(partial(self.stop_btn.setEnabled, False))
        button_layout.addWidget(self.select_all_btn)
        button_layout.addWidget(self.clear_selection_btn)
        button_layout.addStretch(1)
        button_layout.addWidget(self.download_btn)
        button_layout.addWidget(self.delete_btn)
        button_layout.addWidget(self.stop_btn)

        self.label_actions = []
        layout = QVBoxLayout()
        if len(labels) > 1:
            label_flow_layout = FlowLayout()
            _label = QLabel()
            _label.setText('Locations:')
            _label.setAlignment(Qt.AlignTop)
            _label.setIndent(5)
            label_flow_layout.addWidget(_label)
            # TODO: Add a status bar to indicate the root being searched
            for search_label in labels:
                if search_label.isChecked():
                    label = QToolButton()
                    label_action = QAction()
                    label_action.setText(search_label.text())
                    label_action.setCheckable(True)
                    label_action.setChecked(True)
                    label_action.setEnabled(False)
                    label.triggered.connect(
                        partial(self.label_toggled, search_label.text())
                    )
                    label.setDefaultAction(label_action)
                    label_flow_layout.addWidget(label)
                    self.label_actions.append(label_action)
            layout.addLayout(label_flow_layout)
        layout.addWidget(self.view)
        layout.addLayout(button_layout)
        self.setLayout(layout)

    def closeEvent(self, event):
        self.closed.emit()
        return super().closeEvent(event)

    def keyPressEvent(self, event):
        key_combo = event.keyCombination().toCombined()
        if key_combo == QKeySequence(Qt.CTRL | Qt.Key_A):
            self.select_all()
        elif key_combo == QKeySequence(Qt.CTRL | Qt.Key_W):
            self.close()
        else:
            super().keyPressEvent(event)

    @Slot(str, object)
    def label_toggled(self, root, action):
        index = self.view.model().index(0, 1)
        parent = QModelIndex()
        if action.isChecked():
            if not self.select_all_btn.isEnabled():
                self.select_all_btn.setEnabled(True)
            for row in self.view.model().match(
                index,
                Qt.DisplayRole,
                root,
                flags=Qt.MatchStartsWith,
                hits=-1,
            ):
                self.view.setRowHidden(row.row(), parent, False)
            for label in self.label_actions:
                if all(
                    not self.view.isRowHidden(row.row(), parent)
                    for row in self.view.model().match(
                        index,
                        Qt.DisplayRole,
                        label.text(),
                        flags=Qt.MatchStartsWith,
                        hits=-1,
                    )
                ):
                    if not label.isChecked():
                        label.setChecked(True)
        else:
            for row in self.view.model().match(
                index,
                Qt.DisplayRole,
                root,
                flags=Qt.MatchStartsWith,
                hits=-1,
            ):
                self.view.setRowHidden(row.row(), parent, True)
                row_sibling = row.siblingAtColumn(0)
                if self.view.model().data(row_sibling) == Qt.Checked:
                    self.view.model().setData(row_sibling, Qt.Unchecked)
                    self.view.selectionModel().select(
                        row,
                        QItemSelectionModel.Rows |
                        QItemSelectionModel.Deselect
                    )
            if all(
                self.view.isRowHidden(row, parent)
                for row in range(self.view.model().rowCount())
            ):
                for label in self.label_actions:
                    label.setChecked(False)
                self.clear_selection()
                self.select_all_btn.setEnabled(False)
                self.disable_action_btns()
            else:
                for label in self.label_actions:
                    if all(
                        self.view.isRowHidden(row.row(), parent)
                        for row in self.view.model().match(
                            index,
                            Qt.DisplayRole,
                            label.text(),
                            flags=Qt.MatchStartsWith,
                            hits=-1,
                        )
                    ):
                        if label.isChecked():
                            label.setChecked(False)

    @Slot()
    def clear_selection(self):
        index = self.view.model().index(0, 0)
        for checkbox in self.view.model().match(
            index,
            Qt.DisplayRole,
            Qt.Checked,
            flags=Qt.MatchExactly,
            hits=-1,
        ):
            self.view.selectionModel().select(
                checkbox,
                QItemSelectionModel.Rows | QItemSelectionModel.Deselect
            )
            self.view.model().setData(checkbox, Qt.Unchecked)
        self.disable_action_btns()
        if not self.select_all_btn.isEnabled():
            self.select_all_btn.setEnabled(True)

    @Slot()
    def select_all(self):
        index = self.view.model().index(0, 0)
        parent = QModelIndex()
        item_checked = False
        for checkbox in self.view.model().match(
            index,
            Qt.DisplayRole,
            Qt.Unchecked,
            flags=Qt.MatchExactly,
            hits=-1,
        ):
            if not self.view.isRowHidden(checkbox.row(), parent):
                self.view.selectionModel().select(
                    checkbox,
                    QItemSelectionModel.Rows | QItemSelectionModel.Select
                )
                self.view.model().setData(checkbox, Qt.Checked)
                if not item_checked:
                    item_checked = True
        for checkbox in self.view.model().match(
            index,
            Qt.DisplayRole,
            '0',
            flags=Qt.MatchExactly,
            hits=-1,
        ):
            if not self.view.isRowHidden(checkbox.row(), parent):
                self.view.selectionModel().select(
                    checkbox,
                    QItemSelectionModel.Rows | QItemSelectionModel.Select
                )
                self.view.model().setData(checkbox, Qt.Checked)
                if not item_checked:
                    item_checked = True
        if item_checked:
            self.enable_action_btns()
            self.select_all_btn.setEnabled(False)

    @Slot(bool)
    def download(self, checked, *, parent=QModelIndex()):
        index = self.view.model().index(0, 0)
        for row in self.view.model().match(
            index,
            Qt.DisplayRole,
            Qt.Checked,
            flags=Qt.MatchExactly,
            hits=-1,
        ):
            if not self.view.isRowHidden(row.row(), parent):
                print(row.siblingAtColumn(1).data())

    @Slot(str)
    def search_completed(self, msg):
        self.stop_btn.setEnabled(False)
        self.view.model().completed()
        if self.view.model().rowCount():
            self.select_all_btn.setEnabled(True)
        if msg in {'Stopped', 'Aborted', 'Completed'}:
            self.setWindowTitle(f'Search Results - {msg}')
            for label in self.label_actions:
                if not label.isEnabled():
                    label.setEnabled(True)
                    label.setCheckable(True)
                    label.setChecked(True)
        else:
            self.setWindowTitle('Search Results')

    @Slot()
    def all_checked(self):
        if self.select_all_btn.isEnabled():
            self.select_all_btn.setEnabled(False)

    @Slot()
    def unchecked(self):
        if not self.select_all_btn.isEnabled():
            self.select_all_btn.setEnabled(True)

    @Slot()
    def enable_action_btns(self):
        if not self.delete_btn.isEnabled():
            self.delete_btn.setEnabled(True)
        if not self.download_btn.isEnabled():
            self.download_btn.setEnabled(True)
        if not self.clear_selection_btn.isEnabled():
            self.clear_selection_btn.setEnabled(True)

    @Slot()
    def disable_action_btns(self):
        if self.delete_btn.isEnabled():
            self.delete_btn.setEnabled(False)
        if self.download_btn.isEnabled():
            self.download_btn.setEnabled(False)
        if self.clear_selection_btn.isEnabled():
            self.clear_selection_btn.setEnabled(False)
        index = self.view.model().index(0, 0)
        if not index.isValid():
            if self.select_all_btn.isEnabled():
                self.select_all_btn.setEnabled(False)
        elif self.view.isRowHidden(index.row(), QModelIndex()):
            if self.select_all_btn.isEnabled():
                self.select_all_btn.setEnabled(False)
        else:
            if not self.view.model().match(
                index,
                Qt.DisplayRole,
                Qt.Unchecked,
                flags=Qt.MatchExactly
            ):
                if self.select_all_btn.isEnabled():
                    self.select_all_btn.setEnabled(False)
