import os

from functools import partial

from cirrus import items, utils, windows
from cirrus.widgets import FlowLayout, FileFilters

from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QRadioButton,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
)

# TODO: Standard overwite/compare/skip dialog


class ConfirmDeleteDialog(QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Please confirm deletion')
        options = (
            QDialogButtonBox.Yes
            | QDialogButtonBox.No
            | QDialogButtonBox.Cancel
        )
        self.dialog = QDialogButtonBox(options)
        self.dialog.accepted.connect(self.accept)
        self.dialog.rejected.connect(self.reject)
        self.layout = QVBoxLayout()
        message = QLabel(
            ('Are you sure you want permanently '
             'delete the selected items?')
        )
        self.layout.addWidget(message)
        self.layout.addWidget(self.dialog)
        self.setLayout(self.layout)


class CreateDirectoryDialog(QDialog):

    def __init__(self, parent=None, folders=None):
        super().__init__(parent)
        # TODO: Deselect/Select All
        #       Wait for re-styling
        self.parent = parent
        self.setWindowTitle('Create Directory')
        self.button_box = QDialogButtonBox()
        self.create_btn = self.button_box.addButton(
            'Create', QDialogButtonBox.ButtonRole.AcceptRole
        )
        self.create_btn.setEnabled(False)
        self.cancel_btn = self.button_box.addButton(
            '&Cancel', QDialogButtonBox.ButtonRole.RejectRole
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.path = QLineEdit()
        self.path.textEdited.connect(self.update_labels_text)
        self.layout = QVBoxLayout()
        self.folder_options = []
        if folders:
            top_message = QLabel('Starting paths to use:')
            top_message.setWordWrap(True)
            message = QLabel(
                ('Please specify the directory path to be '
                 'created in the selected common working directories')
            )
            message.setWordWrap(True)
            self.layout.addWidget(top_message)
            options_layout = QGridLayout()
            options_layout.setColumnMinimumWidth(0, 10)
            options_layout.setColumnMinimumWidth(2, 5)
            options_layout.setColumnStretch(4, 1)
            __processed = set()
            for row, folder in enumerate(folders):
                if folder.root not in __processed:
                    path = os.path.join(self.parent.root, folder.root)
                    label = QLabel()
                    label.setTextFormat(Qt.RichText)
                    label.setText(f'<p>{path}</p>')
                    checkbox = QCheckBox()
                    checkbox.setCheckState(Qt.Checked)
                    checkbox.stateChanged.connect(
                        partial(self.checkbox_selected, label)
                    )
                    options_layout.addWidget(checkbox, row, 1)
                    options_layout.addWidget(label, row, 3)
                    self.folder_options.append((path, checkbox, label))
                    __processed.add(folder.root)
            options_layout.setRowStretch(row + 1, 1)
        else:
            message = QLabel('Please specify the directory path to be created')
            message.setWordWrap(True)
            options_layout = QGridLayout()
            options_layout.setColumnMinimumWidth(0, 10)
            options_layout.setColumnStretch(3, 1)
            checkbox = QCheckBox()
            checkbox.setCheckState(Qt.Checked)
            checkbox.hide()
            label = QLabel(f'<p>{self.parent.root}</p>')
            options_layout.addWidget(checkbox, 0, 1)
            options_layout.addWidget(label, 0, 2)
            options_layout.setRowStretch(1, 1)
            self.folder_options.append((self.parent.root, checkbox, label))
        self.layout.addLayout(options_layout)
        self.layout.addWidget(message)
        self.layout.addWidget(self.path)
        self.layout.addWidget(self.button_box)
        self.setLayout(self.layout)

    @Slot(str)
    def update_labels_text(self, text):
        text = text.lstrip('\\').lstrip('/')
        if not text:
            self.create_btn.setEnabled(False)
        elif not self.create_btn.isEnabled():
            self.create_btn.setEnabled(True)
        for path, checkbox, label in self.folder_options:
            new_path = os.path.join(path, text)
            if checkbox.isChecked():
                label.setText(f'<p>{new_path}</p>')
            else:
                label.setText(f'<p style="color:grey;">{new_path}</p>')

    @Slot(partial)
    def checkbox_selected(self, label, state):
        path = utils.html_to_text(label.text())
        if state == 0:  # unchecked
            label.setText(f'<p style="color:grey;">{path}</p>')
            if self.all_checkboxes_deselected():
                self.create_btn.setEnabled(False)
        else:
            label.setText(f'<p>{path}</p>')
            if not self.create_btn.isEnabled():
                self.create_btn.setEnabled(True)

    def all_checkboxes_deselected(self):
        for _, checkbox, _ in self.folder_options:
            if checkbox.isChecked():
                return False
        return True


class SearchItemsDialog(QDialog):

    def __init__(self, *, parent=None, folders=None, destinations=None):
        super().__init__(parent)
        self.setSizePolicy(
            QSizePolicy.Minimum,
            QSizePolicy.Minimum
        )
        self.setMinimumWidth(600)
        self.setMinimumHeight(200)
        self.parent = parent
        __processed_folders = set()
        self.folders = []
        if folders:
            for folder in folders:
                if folder.root not in __processed_folders:
                    self.folders.append(folder)
                    __processed_folders.add(folder.root)
        elif isinstance(parent, windows.main.MainWindow):
            for _, account in parent.central_widget.splitter_listing_panels:
                if account['Root'].rstrip('/') not in __processed_folders:
                    self.folders.append(items.account_to_item(account))
                    __processed_folders.add(account['Root'].rstrip('/'))
        else:
            # TODO: Re-evaluate account v. user
            user = self.parent.user.copy()
            if self.parent.type == 's3':
                self.folders.append(items.S3Item(user, is_dir=True))
            if self.parent.type == 'digital ocean':
                self.folders.append(items.DigitalOceanItem(user, is_dir=True))
            elif self.parent.type == 'local':
                self.folders.append(items.LocalItem(user, is_dir=True))
            else:
                raise ValueError(f'No Item-type for {self.parent.type}')
        self.folders.sort(key=lambda x: x.root)
        __processed_dests = set()
        self.destinations = []
        if destinations:
            for dest in destinations:
                if dest.root not in __processed_dests:
                    self.destinations.append(dest)
                    __processed_dests.add(dest.root)
        self.destinations.sort(key=lambda x: x.root)
        self.setWindowTitle('Search')
        self.recursive = False
        self.button_box = QDialogButtonBox()
        self.search_btn = self.button_box.addButton(
            '&Search', QDialogButtonBox.ButtonRole.AcceptRole
        )
        self.recursive_search_btn = self.button_box.addButton(
            '&Recursive Search', QDialogButtonBox.ButtonRole.AcceptRole
        )
        self.recursive_search_btn.clicked.connect(self.toggle_recursive)
        self.cancel_btn = self.button_box.addButton(
            '&Cancel', QDialogButtonBox.ButtonRole.RejectRole
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

        # Filters
        self.filters = FileFilters(window=self.parent)
        filters_form = self.filters.setup_form()

        self.layout = QVBoxLayout()
        self.location_selections = []
        if len(self.folders) > 1:
            flow_layout = FlowLayout()
            _label = QLabel()
            _label.setTextFormat(Qt.RichText)
            _label.setText('<b>Locations:</b>')
            _label.setAlignment(Qt.AlignTop)
            _label.setIndent(5)
            flow_layout.addWidget(_label)
            for folder in self.folders:
                label = QToolButton()
                label.setText(folder.root)
                label.setCheckable(True)
                label.setChecked(True)
                label.toggled.connect(partial(self.location_selected, label))
                self.location_selections.append(label)
                flow_layout.addWidget(label)
            self.layout.addLayout(flow_layout)
        else:
            self.layout.addWidget(
                QLabel(
                    f'<b>Starting from... {self.folders[0].root}</b>'
                )
            )
        self.layout.addLayout(filters_form)
        self.layout.addWidget(self.button_box)
        self.setLayout(self.layout)
        self.filters.after_setup_styling()

    def location_selected(self, label, checked):
        if checked:
            for btn in self.button_box.buttons():
                if not btn.isEnabled():
                    btn.setEnabled(True)
        else:
            if self.all_locations_deselected():
                for btn in self.button_box.buttons():
                    btn.setEnabled(False)

    def all_locations_deselected(self):
        return not any(
            btn.isChecked() for btn in self.location_selections
        )

    @Slot(bool)
    def toggle_recursive(self):
        self.recursive = False if self.recursive else True


class TransferItemsDialog(QDialog):

    def __init__(self, *, parent, folders, destinations):
        super().__init__(parent)
        self.setSizePolicy(
            QSizePolicy.Minimum,
            QSizePolicy.Minimum
        )
        self.setMinimumWidth(600)
        self.setMinimumHeight(200)
        self.parent = parent
        __processed_folders = set()
        self.folders = []
        if folders:
            for folder in folders:
                if folder.root not in __processed_folders:
                    self.folders.append(folder)
                    __processed_folders.add(folder.root)
        elif isinstance(parent, windows.main.MainWindow):
            for _, account in parent.central_widget.splitter_listing_panels:
                if account['Root'].rstrip('/') not in __processed_folders:
                    self.folders.append(items.account_to_item(account))
                    __processed_folders.add(account['Root'].rstrip('/'))
        else:
            # TODO: Re-evaluate account v. user
            user = self.parent.user.copy()
            if self.parent.type == 's3':
                self.folders.append(items.S3Item(user, is_dir=True))
            if self.parent.type == 'digital ocean':
                self.folders.append(items.DigitalOceanItem(user, is_dir=True))
            elif self.parent.type == 'local':
                self.folders.append(items.LocalItem(user, is_dir=True))
            else:
                raise ValueError(f'No Item-type for {self.parent.type}')
        self.folders.sort(key=lambda x: x.root)
        __processed_dests = set()
        self.destinations = []
        if destinations:
            for dest in destinations:
                if dest.root not in __processed_dests:
                    self.destinations.append(dest)
                    __processed_dests.add(dest.root)
        self.destinations.sort(key=lambda x: x.root)
        self.setWindowTitle('Advanced Copy')
        self.recursive = False
        button_bar_layout = QHBoxLayout()
        self.button_box = QDialogButtonBox()
        self.search_btn = self.button_box.addButton(
            '&Copy', QDialogButtonBox.ButtonRole.AcceptRole
        )
        self.recursive_search_btn = self.button_box.addButton(
            '&Recursive Copy', QDialogButtonBox.ButtonRole.AcceptRole
        )
        self.recursive_search_btn.clicked.connect(self.toggle_recursive)
        self.cancel_btn = self.button_box.addButton(
            '&Cancel', QDialogButtonBox.ButtonRole.RejectRole
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

        # Process Option Group
        radio_group = QButtonGroup(self)
        self.add_to_queue_radio = QRadioButton('Add Matches to Queue')
        self.add_to_queue_radio.setChecked(True)
        self.add_and_start_radio = QRadioButton('Process Queue')
        radio_group.addButton(self.add_to_queue_radio)
        radio_group.addButton(self.add_and_start_radio)
        button_bar_layout.addWidget(self.add_to_queue_radio)
        button_bar_layout.addWidget(self.add_and_start_radio)
        button_bar_layout.addStretch(1)
        button_bar_layout.addWidget(self.button_box)

        # Filters
        self.filters = FileFilters(window=self.parent)
        filters_form = self.filters.setup_form()

        # This will be a pop-up
        # Overwrite (Plain)
        #   Source is Newer
        #   Different Size
        #   Size or Source
        #   Hash (algo)
        # Rename (make it simple, stupid, i.e., (n+1).ext)
        # Skip

        self.layout = QVBoxLayout()
        selection_grid = QGridLayout()
        selection_grid.setColumnStretch(1, 1)
        self.location_selections = []
        # From sources
        if len(self.folders) > 1:
            flow_layout = FlowLayout()
            _label = QLabel()
            _label.setTextFormat(Qt.RichText)
            _label.setText('<b>From:</b>')
            _label.setAlignment(Qt.AlignRight)
            _label.setIndent(5)
            selection_grid.addWidget(_label, 0, 0)
            for folder in self.folders:
                label = QToolButton()
                label.setText(folder.root)
                label.setCheckable(True)
                label.setChecked(True)
                label.toggled.connect(partial(self.location_selected, label))
                self.location_selections.append(label)
                flow_layout.addWidget(label)
            selection_grid.addLayout(flow_layout, 0, 1)
        else:
            f_label = QLabel()
            f_label.setTextFormat(Qt.RichText)
            f_label.setAlignment(Qt.AlignRight)
            f_label.setText('<b>From:</b>')
            r_label = QLabel()
            r_label.setText(self.folders[0].root)
            selection_grid.addWidget(f_label, 0, 0)
            selection_grid.addWidget(r_label, 0, 1)
        # Destination outputs
        self.destination_selections = []
        if len(self.destinations) > 1:
            flow_layout = FlowLayout()
            _label = QLabel()
            _label.setTextFormat(Qt.RichText)
            _label.setText('<b>Destinations:</b>')
            _label.setAlignment(Qt.AlignRight)
            _label.setIndent(5)
            selection_grid.addWidget(_label, 1, 0)
            for dst in self.destinations:
                label = QToolButton()
                label.setText(dst.root)
                label.setCheckable(True)
                label.setChecked(True)
                label.toggled.connect(partial(self.location_selected, label))
                self.destination_selections.append(label)
                flow_layout.addWidget(label)
            selection_grid.addLayout(flow_layout, 1, 1)
        else:
            f_label = QLabel()
            f_label.setTextFormat(Qt.RichText)
            f_label.setAlignment(Qt.AlignRight)
            f_label.setText('<b>Destination:</b>')
            r_label = QLabel()
            r_label.setText(self.destinations[0].root)
            selection_grid.addWidget(f_label, 1, 0)
            selection_grid.addWidget(r_label, 1, 1)
        self.layout.addLayout(selection_grid)
        self.layout.addLayout(filters_form)
        self.layout.addLayout(button_bar_layout)
        self.setLayout(self.layout)
        self.filters.after_setup_styling()

    def location_selected(self, label, checked):
        if self.all_locations_deselected():
            for btn in self.button_box.buttons():
                btn.setEnabled(False)
        else:
            for btn in self.button_box.buttons():
                if not btn.isEnabled():
                    btn.setEnabled(True)

    def all_locations_deselected(self):
        if self.location_selections:
            has_selection = any(
                btn.isChecked() for btn in self.location_selections
            )
        else:
            has_selection = True
        if self.destination_selections:
            has_destination = any(
                btn.isChecked() for btn in self.destination_selections
            )
        else:
            has_destination = True
        return not all((has_destination, has_selection))

    @Slot(bool)
    def toggle_recursive(self):
        self.recursive = False if self.recursive else True
