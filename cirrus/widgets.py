import logging
import os

from cirrus import utils, windows
from cirrus.models import ListModel

from PySide6.QtCore import (
    QDate,
    QMargins,
    QModelIndex,
    QPoint,
    QRect,
    QSize,
    Qt,
    Signal,
    Slot,
)
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDateEdit,
    QFormLayout,
    QHBoxLayout,
    QLayout,
    QLineEdit,
    QListView,
    QSizePolicy,
    QSpinBox,
    QWidget,
)


class FileFilters(QWidget):

    def __init__(self, *, parent=None, window=None):
        super().__init__(parent)
        self.window = window

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

    def setup_form(self):
        form = QFormLayout()
        form.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        form.addRow('Name:', self.name_layout)
        form.addRow('Filetype:', self.file_types_layout)
        form.addRow('Creation Time:', self.ctime_layout)
        if self.window:
            if not isinstance(self.window, windows.main.MainWindow):
                if self.window.type == 's3':
                    form.setRowVisible(2, False)
        form.addRow('Modified Time:', self.mtime_layout)
        form.addRow('Size:', self.size_layout)
        return form

    def after_setup_styling(self):
        # After creation modifications
        self.name.setFocus()
        option_col_width = self.name_option.minimumSizeHint().width()
        self.ctime_option.setMinimumWidth(option_col_width)
        self.mtime_option.setMinimumWidth(option_col_width)
        self.size_option_increment.setMinimumWidth(
            self.mtime_option_increment.minimumSizeHint().width()
        )
        self.size_option.setMinimumWidth(option_col_width)

    def setup_name_selection(self):
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


class FlowLayout(QLayout):

    def __init__(self, parent=None, size_policy=QSizePolicy.ToolButton):
        super().__init__(parent)
        if parent is not None:
            self.setContentsMargins(QMargins(0, 0, 0, 0))
        self.size_policy = size_policy
        self._item_list = []

    def __del__(self):
        item = self.takeAt(0)
        while item:
            item = self.takeAt(0)

    def addItem(self, item):
        self._item_list.append(item)

    def count(self):
        return len(self._item_list)

    def itemAt(self, index):
        if 0 <= index < len(self._item_list):
            return self._item_list[index]

    def takeAt(self, index):
        if 0 <= index < len(self._item_list):
            return self._item_list.pop(index)

    def expandingDirections(self):
        return Qt.Orientation(0)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        return self._do_layout(QRect(0, 0, width, 0), test_only=True)

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self._do_layout(rect, test_only=False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()
        for item in self._item_list:
            size = size.expandedTo(item.minimumSize())
        size += QSize(
            2 * self.contentsMargins().top(), 2 * self.contentsMargins().top()
        )
        return size

    def _do_layout(self, rect, *, test_only):
        x = rect.x()
        y = rect.y()
        line_height = 0
        spacing = self.spacing()
        for item in self._item_list:
            style = item.widget().style()
            layout_spacing_x = style.layoutSpacing(
                self.size_policy,
                self.size_policy,
                Qt.Horizontal
            )
            layout_spacing_y = style.layoutSpacing(
                self.size_policy,
                self.size_policy,
                Qt.Vertical
            )
            space_x = spacing + layout_spacing_x
            space_y = spacing + layout_spacing_y
            next_x = x + item.sizeHint().width() + space_x
            if next_x - space_x > rect.right() and line_height > 0:
                x = rect.x()
                y = y + line_height + space_y
                next_x = x + item.sizeHint().width() + space_x
                line_height = 0
            if not test_only:
                item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))
            x = next_x
            line_height = max(line_height, item.sizeHint().height())
        return y + line_height - rect.y()


class NavBarLineEdit(QLineEdit):
    selection_made = Signal(str)

    def __init__(self, parent):
        super().__init__(parent)
        self.model = ListModel([])
        self.view = NavBarListView(parent)
        self.view.setModel(self.model)
        self.view.selection_made.connect(self.selection_made.emit)
        self.returnPressed.connect(self.clear_focus)

    def set_model(self, items):
        cleaned_items = []
        for item in items:
            if item not in cleaned_items:
                cleaned_items.append(item)
        self.model.update_items(cleaned_items)

    @Slot()
    def clear_focus(self):
        self.clearFocus()
        self.view.hide()

    def focusInEvent(self, event):
        if (row_count := self.view.model().rowCount()) > 0:
            self.view.show()
            height = row_count * self.view.sizeHintForRow(0)
            frame = self.frameGeometry()
            self.view.setGeometry(
                frame.x() - 10,
                self.view.y(),
                frame.width(),
                height + 5,
            )
        return super().focusInEvent(event)

    def focusOutEvent(self, event):
        self.clear_focus()
        return super().focusOutEvent(event)


class NavBarListView(QListView):
    selection_made = Signal(str)

    def __init__(self, parent):
        super().__init__(parent)
        self.hide()
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setUniformItemSizes(True)
        self.setTextElideMode(Qt.ElideMiddle)
        self.setDragDropMode(QAbstractItemView.NoDragDrop)
        self.setMouseTracking(True)
        self.clicked.connect(self.location_clicked)
        self.entered.connect(self.on_hover)

    @Slot(QModelIndex)
    def location_clicked(self, index):
        if data := index.data():
            self.selection_made.emit(data)

    @Slot(QModelIndex)
    def on_hover(self, index):
        if not index.isValid():
            return
        self.setCurrentIndex(index)


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
