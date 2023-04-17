from functools import partial

from cirrus.models import SearchResultsModel
from cirrus.views.search import SearchResultsTreeView

from PySide6.QtCore import Qt, QItemSelectionModel, QModelIndex, Slot, Signal
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QToolButton,
    QVBoxLayout,
    QWidget,
)


class SearchResultsWindow(QWidget):
    aborted = Signal()
    closed = Signal()

    def __init__(self, folders):
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
        if len(folders) > 1:
            label_layout = QHBoxLayout()
            label_layout.addWidget(QLabel('Locations:'))
            for folder in folders:
                label = QToolButton()
                label_action = QAction()
                label_action.setText(folder.root)
                label_action.setCheckable(True)
                label_action.setChecked(True)
                label.triggered.connect(
                    partial(self.label_toggled, folder.root)
                )
                label.setDefaultAction(label_action)
                label_layout.addWidget(label)
                self.label_actions.append(label_action)
            label_layout.addStretch(1)
            layout.addLayout(label_layout)
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
            return super().keyPressEvent(event)

    @Slot(str, object)
    def label_toggled(self, root, action):
        if (index := self.view.model().index(0, 1)).isValid():
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
                self.view.selectionModel().select(
                    checkbox,
                    QItemSelectionModel.Rows | QItemSelectionModel.Deselect
                )
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
            self.disable_action_btns()
            if not self.select_all_btn.isEnabled():
                self.select_all_btn.setEnabled(True)

    @Slot()
    def select_all(self):
        if (index := self.view.model().index(0, 0)).isValid():
            if self.view.isRowHidden(index.row(), QModelIndex()):
                return
            parent = QModelIndex()
            top_left = None
            bottom_right = None
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
                if not self.view.isRowHidden(checkbox.row(), parent):
                    self.view.selectionModel().select(
                        checkbox,
                        QItemSelectionModel.Rows | QItemSelectionModel.Select
                    )
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
            self.enable_action_btns()
            self.select_all_btn.setEnabled(False)

    @Slot(bool)
    def download(self, checked, *, parent=QModelIndex()):
        if (index := self.view.model().index(0, 0)).isValid():
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
        if self.view.model().rowCount():
            self.select_all_btn.setEnabled(True)
        if msg in {'Stopped', 'Aborted', 'Completed'}:
            self.setWindowTitle(f'Search Results - {msg}')
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
