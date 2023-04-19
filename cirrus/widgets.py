from cirrus.models import ListModel

from PySide6.QtCore import (
    QMargins,
    QPoint,
    QRect,
    QSize,
    Qt,
    Signal,
    Slot,
    QModelIndex,
)
from PySide6.QtWidgets import (
    QAbstractItemView,
    QLineEdit,
    QLayout,
    QListView,
    QSizePolicy,
)


class FlowLayout(QLayout):

    def __init__(self, parent=None):
        super().__init__(parent)
        if parent is not None:
            self.setContentsMargins(QMargins(0, 0, 0, 0))
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
        return self._do_layout(QRect(0, 0, width, 0), True)

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self._do_layout(rect, False)

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

    def _do_layout(self, rect, test_only):
        x = rect.x()
        y = rect.y()
        line_height = 0
        spacing = self.spacing()
        for item in self._item_list:
            style = item.widget().style()
            layout_spacing_x = style.layoutSpacing(
                QSizePolicy.ToolButton,
                QSizePolicy.ToolButton,
                Qt.Horizontal
            )
            layout_spacing_y = style.layoutSpacing(
                QSizePolicy.ToolButton,
                QSizePolicy.ToolButton,
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
        self.view = NavBarListView(parent)
        self.view.selection_made.connect(self.selection_made.emit)
        self.returnPressed.connect(self.clear_focus)

    def set_model(self, items):
        cleaned_items = []
        for item in items:
            if item not in cleaned_items:
                cleaned_items.append(item)
        model = ListModel(cleaned_items)
        prev_model = self.view.model()
        prev_selection_model = self.view.selectionModel()
        self.view.setModel(model)
        if prev_model:
            prev_model.deleteLater()
        if prev_selection_model:
            prev_selection_model.deleteLater()

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
