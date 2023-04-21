import logging
import os

from functools import partial

from cirrus import items, utils, windows
from cirrus.widgets import FlowLayout

from PySide6.QtCore import QDate, Qt, Slot
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QFormLayout,
    QGridLayout,
    QLabel,
    QLineEdit,
    QSizePolicy,
    QSpinBox,
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
            ('Are you sure you want permanently'
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
                    __processed.add(folder.oot)
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

    # TODO: Searches for downloading, uploading, searching
    # TODO: Files, Files and Dirs, Dirs
    # TODO: When multiple folders, results window will use toggle buttons
    #       to show/hide those reults
    #       Select/De-Select All <-> [folder toggles] <-> Action Buttons

    def __init__(self, *, parent=None, folders=None):
        super().__init__(parent)
        self.setSizePolicy(
            QSizePolicy.Minimum,
            QSizePolicy.Minimum
        )
        self.setMinimumWidth(600)
        self.setMinimumHeight(200)
        self.parent = parent
        __processed = set()
        self.folders = []
        if folders:
            for folder in folders:
                print(folder.root)
                if folder.root not in __processed:
                    self.folders.append(folder)
                    __processed.add(folder.root)
        elif isinstance(parent, windows.main.MainWindow):
            for _, account in parent.central_widget.splitter_listing_panels:
                if account['Root'].rstrip('/') not in __processed:
                    self.folders.append(items.account_to_item(account))
                    __processed.add(account['Root'].rstrip('/'))
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
        self.setWindowTitle('Search')
        self.recursive = False
        self.button_box = QDialogButtonBox()
        self.search_btn = self.button_box.addButton(
            '&Search', QDialogButtonBox.ButtonRole.AcceptRole
        )
        self.recursive_search_button = self.button_box.addButton(
            '&Recursive Search', QDialogButtonBox.ButtonRole.AcceptRole
        )
        self.recursive_search_button.clicked.connect(self.toggle_recursive)
        self.cancel_btn = self.button_box.addButton(
            '&Cancel', QDialogButtonBox.ButtonRole.RejectRole
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

        # Name Field
        __name = self.setup_name_selection()
        self.name, self.name_option, self.name_layout = __name

        # File Type Field
        __ftypes = self.setup_file_type_selection()
        self.file_types = __ftypes[0]
        self.file_types_option = __ftypes[1]
        self.file_types_layout = __ftypes[2]

        # Creation Time Field
        __ctime = self.setup_ctime_selection()
        self.ctime, self.ctime_option, self.ctime_layout = __ctime
        self.ctime_option.currentTextChanged.connect(
            self.ctime_selection_change
        )
        self.ctime_layout.setStretch(1, 1)

        # Modified Time Field
        __mtime = self.setup_mtime_selection()
        self.mtime, self.mtime_option, self.mtime_layout = __mtime
        self.mtime_option.currentTextChanged.connect(
            self.mtime_selection_change
        )
        self.mtime_layout.setStretch(1, 1)

        # Size Field
        __size = self.setup_size_selection()
        self.size, self.size_option, self.size_layout = __size
        self.size_layout.setStretch(1, 1)

        form = QFormLayout()
        form.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        form.addRow('Name:', self.name_layout)
        form.addRow('Filetype:', self.file_types_layout)
        form.addRow('Creation Time:', self.ctime_layout)
        if self.parent and not isinstance(parent, windows.main.MainWindow):
            if self.parent.type == 's3':
                form.setRowVisible(2, False)
        form.addRow('Modified Time:', self.mtime_layout)
        form.addRow('Size:', self.size_layout)

        self.layout = QVBoxLayout()
        self.location_selections = []
        if len(self.folders) > 1:
            flow_layout = FlowLayout()
            _label = QLabel()
            _label.setText('Locations:')
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
                    f'Searching in... {self.folders[0].root}'
                )
            )
        self.layout.addLayout(form)
        self.layout.addWidget(self.button_box)
        self.setLayout(self.layout)

        # After creation modifications
        self.name.setFocus()
        option_col_width = self.name_option.minimumSizeHint().width()
        self.ctime_option.setMinimumWidth(option_col_width)
        self.mtime_option.setMinimumWidth(option_col_width)
        self.size_option_increment.setMinimumWidth(
            self.mtime_option_increment.minimumSizeHint().width()
        )
        self.size_option.setMinimumWidth(option_col_width)

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
        for btn in self.location_selections:
            if btn.isChecked():
                return False
        return True

    def setup_name_selection(self):
        # Name: contains, starts, ends, exact
        #       case sensitive, case insensitive
        #       qlineedit, dropdown
        layout = QHBoxLayout()
        options = [
            ('Contains', name_contains),
            ('Does Not Contain', name_does_not_contain),
            ('Equals', name_equals),
            ('Starts with', name_starts_with),
            ('Ends with', name_ends_with),
        ]
        name_option = QComboBox()
        for index, option in enumerate(options):
            text, func = option
            name_option.addItem(text)
            name_option.setItemData(index, func)
        name = QLineEdit()
        name.setPlaceholderText('File types will be ignored')
        layout.addWidget(name_option)
        layout.addWidget(name)
        return name, name_option, layout

    def setup_file_type_selection(self):
        # Filetype: comma seperated values
        #           contains, not contains
        #           qlineedit, dropdown
        layout = QHBoxLayout()
        file_types_option = QComboBox()
        options = [
            ('Equals', extension_equals),
            ('Not Equal', extension_not_equals),
            ('Contains', extension_contains),
            ('Does Not Contain', extension_does_not_contain),
            ('Starts with', extension_starts_with),
            ('Ends with', extension_ends_with),
        ]
        for index, option in enumerate(options):
            text, func = option
            file_types_option.addItem(text)
            file_types_option.setItemData(index, func)
        file_types = QLineEdit()
        file_types.setPlaceholderText(
            'Seperated by commas, e.g., .jpg,png. Case insensitive.'
        )
        layout.addWidget(file_types_option)
        layout.addWidget(file_types)
        return file_types, file_types_option, layout

    def setup_ctime_selection(self):
        # CTime: before, after, equal
        #        seconds, minutes, hours
        #        qlineedit, dropdown
        ctime_layout = QHBoxLayout()
        self.ctime_selections = {
            'Within Last': ['Days', 'Hours', 'Minutes', 'Seconds'],
            'Before': self.date_edit_today,
            'After': self.date_edit_today,
        }
        ctime_option = QComboBox()
        options = [
            ('Within Last', within_last_ctime),
            ('Before', before_ctime),
            ('After', after_ctime),
        ]
        for index, option in enumerate(options):
            text, func = option
            ctime_option.addItem(text)
            ctime_option.setItemData(index, func)
        ctime = QSpinBox()
        ctime.setMinimum(0)
        ctime.setMaximum(999)
        self.ctime_option_increment = QComboBox()
        self.ctime_option_increment.addItems(
            self.ctime_selections['Within Last']
        )
        ctime_layout.addWidget(ctime_option)
        ctime_layout.addWidget(ctime)
        ctime_layout.addWidget(self.ctime_option_increment)
        return ctime, ctime_option, ctime_layout

    def setup_mtime_selection(self):
        mtime_layout = QHBoxLayout()
        self.mtime_selections = {
            'Within Last': ['Days', 'Hours', 'Minutes', 'Seconds'],
            'Before': self.date_edit_today,
            'After': self.date_edit_today,
        }
        mtime_option = QComboBox()
        options = [
            ('Within Last', within_last_mtime),
            ('Before', before_mtime),
            ('After', after_mtime),
        ]
        for index, option in enumerate(options):
            text, func = option
            mtime_option.addItem(text)
            mtime_option.setItemData(index, func)
        mtime = QSpinBox()
        mtime.setMinimum(0)
        mtime.setMaximum(999)
        self.mtime_option_increment = QComboBox()
        self.mtime_option_increment.addItems(
            self.mtime_selections['Within Last']
        )
        mtime_layout.addWidget(mtime_option)
        mtime_layout.addWidget(mtime)
        mtime_layout.addWidget(self.mtime_option_increment)
        return mtime, mtime_option, mtime_layout

    def setup_size_selection(self):
        # Size: >, <, =
        #       byte, kb, mb, gb
        #       qlinedit, dropdown
        size_layout = QHBoxLayout()
        size_option = QComboBox()
        options = [
            ('>', greater_than),
            ('<', less_than),
            ('=', equals),
            ('>=', greater_equal_to),
            ('<=', lesser_equal_to),
        ]
        for index, option in enumerate(options):
            text, func = option
            size_option.addItem(text)
            size_option.setItemData(index, func)
        size = QSpinBox()
        size.setMinimum(0)
        size.setMaximum(9999)
        self.size_option_increment = QComboBox()
        self.size_option_increment.addItems(['B', 'KB', 'MB', 'GB'])
        size_layout.addWidget(size_option)
        size_layout.addWidget(size)
        size_layout.addWidget(self.size_option_increment)
        return size, size_option, size_layout

    @Slot(bool)
    def toggle_recursive(self):
        self.recursive = False if self.recursive else True

    @Slot(str)
    def ctime_selection_change(self, text):
        if option := self.ctime_selections.get(text):
            self.ctime_layout.removeWidget(self.ctime)
            self.ctime.deleteLater()
            self.ctime.parent = None
            self.ctime = None
            if isinstance(option, list):
                self.ctime_option_increment.show()
                self.ctime = QSpinBox()
                self.ctime.setMinimum(0)
                self.ctime.setMaximum(999)
            else:
                self.ctime_option_increment.hide()
                self.ctime = option()
            self.ctime_layout.insertWidget(1, self.ctime)
        else:
            logging.warn(
                f'Received invalid option {text} for ctime_option_increment'
            )
            self.ctime_option_increment.show()
            self.ctime_layout.removeWidget(self.ctime)
            self.ctime.deleteLater()
            self.ctime = None
            self.ctime = QLineEdit()

    @Slot(str)
    def mtime_selection_change(self, text):
        if option := self.mtime_selections.get(text):
            self.mtime_layout.removeWidget(self.mtime)
            self.mtime.deleteLater()
            self.mtime.parent = None
            self.mtime = None
            if isinstance(option, list):
                self.mtime_option_increment.show()
                self.mtime = QSpinBox()
                self.mtime.setMinimum(0)
                self.mtime.setMaximum(999)
            else:
                self.mtime_option_increment.hide()
                self.mtime = option()
            self.mtime_layout.insertWidget(1, self.mtime)
        else:
            logging.warn(
                f'Received invalid option {text} for mtime_option_increment'
            )
            self.mtime_option_increment.show()
            self.mtime_layout.removeWidget(self.mtime)
            self.mtime.deleteLater()
            self.mtime = None
            self.mtime = QLineEdit()

    def date_edit_today(self):
        today = utils.date.now()
        date = QDate(today.year, today.month, today.day)
        date_edit = QDateEdit(date)
        date_edit.setDisplayFormat('yyyy-MM-dd')
        return date_edit


def name_equals(value, item, icase=True):
    tail = os.path.split(item.root.rstrip('/').rstrip('\\'))[1]
    tail = os.path.splitext(tail)[0]
    if icase:
        return tail.lower() == str(value).lower()
    return tail == str(value)


def extension_equals(value, item, icase=True):
    ext = os.path.splitext(item.root)[1]
    if icase:
        return ext.lower() == str(value).lower()
    return ext == str(value)


def name_not_equals(value, item, icase=True):
    return not name_equals(value, item, icase=icase)


def extension_not_equals(value, item, icase=True):
    return not extension_equals(value, item, icase=icase)


def name_contains(value, item, icase=True):
    tail = os.path.split(item.root.rstrip('/').rstrip('\\'))[1]
    tail = os.path.splitext(tail)[0]
    if icase:
        return str(value).lower() in tail.lower()
    return str(value) in tail


def extension_contains(value, item, icase=True):
    ext = os.path.splitext(item.root)[1]
    if icase:
        return str(value).lower() in ext.lower()
    return str(value) in ext


def name_does_not_contain(value, item, icase=True):
    return not name_contains(value, item, icase=icase)


def extension_does_not_contain(value, item, icase=True):
    return not extension_contains(value, item, icase=icase)


def name_ends_with(value, item, icase=True):
    tail = os.path.split(item.root.rstrip('/').rstrip('\\'))[1]
    tail = os.path.splitext(tail)[0]
    if icase:
        return tail.lower().endswith(str(value).lower())
    return tail.endswith(str(value))


def extension_ends_with(value, item, icase=True):
    ext = os.path.splitext(item.root)[1]
    if icase:
        return ext.lower().endswith(str(value).lower())
    return ext.endswith(str(value))


def name_starts_with(value, item, icase=True):
    tail = os.path.split(item.root.rstrip('/').rstrip('\\'))[1]
    tail = os.path.splitext(tail)[0]
    if icase:
        return tail.lower().startswith(str(value).lower())
    return tail.startswith(str(value))


def extension_starts_with(value, item, icase=True):
    ext = os.path.splitext(item.root)[1]
    if icase:
        return ext.lower().startswith(str(value).lower())
    return ext.startswith(str(value))


def equals(value, item):
    return item.size == int(value)


def greater_than(value, item):
    return item.size > int(value)


def less_than(value, item):
    return item.size < int(value)


def greater_equal_to(value, item):
    return item.size >= int(value)


def lesser_equal_to(value, item):
    return item.size <= int(value)


def within_last_ctime(item, compare_date, seconds):
    if start_date := item.ctime:
        if start_date > compare_date:
            if (start_date - compare_date).seconds <= seconds:
                return True
    return False


def within_last_mtime(item, compare_date, seconds):
    if start_date := item.mtime:
        if start_date > compare_date:
            if (start_date - compare_date).seconds <= seconds:
                return True
    return False


def before_ctime(item, compare_date):
    return item.ctime < compare_date


def before_mtime(item, compare_date):
    return item.mtime < compare_date


def after_ctime(item, compare_date):
    return item.ctime > compare_date


def after_mtime(item, compare_date):
    return item.mtime > compare_date
