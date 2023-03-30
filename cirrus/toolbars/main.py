from functools import partial

from cirrus import settings

from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QHBoxLayout,
    QPushButton,
    QStyle,
    QToolBar,
    QWidget,
    QWidgetAction,
)


class CustomAddComboBox(QComboBox):

    def __init__(self, instance, parent=None):
        super().__init__(parent)
        self.instance = instance
        self.currentTextChanged.connect(self.reset_index)
        self.currentIndexChanged.connect(self.account_selected)
        self.focus_in = True

    @Slot(int)
    def reset_index(self, text):
        self.setCurrentIndex(-1)

    @Slot(int)
    def account_selected(self, index):
        if index >= 0 and not self.focus_in:
            if account := self.itemData(index):
                self.instance.add_splitter_panel(account)

    def reset_options(self):
        self.clear()
        for account in settings.saved_users():
            text = f'({account["Type"]}) {account["Root"]}'
            self.addItem(text, userData=account)

    def focusInEvent(self, event):
        if event.reason() == Qt.MouseFocusReason:
            self.reset_options()
            self.focus_in = True
            event.accept()
        else:
            self.focus_in = False
            return super().focusInEvent(event)


class CustomRemoveComboBox(QComboBox):

    def __init__(self, instance, parent=None):
        super().__init__(parent)
        self.instance = instance
        self.currentTextChanged.connect(self.reset_index)
        self.currentIndexChanged.connect(self.account_selected)
        self.focus_in = True

    @Slot(int)
    def reset_index(self, index):
        self.setCurrentIndex(-1)

    @Slot(int)
    def account_selected(self, index):
        if not self.focus_in:
            if (panel := self.itemData(index)) is not None:
                self.instance.remove_splitter_panel(panel)

    def reset_options(self):
        self.clear()
        for idx, (_, account) in enumerate(
            self.instance.splitter_listing_panels
        ):
            text = f'({account["Type"]}) {account["Root"]}'
            self.addItem(text, userData=idx)

    def focusInEvent(self, event):
        if event.reason() == Qt.MouseFocusReason:
            self.reset_options()
            self.focus_in = True
            event.accept()
        else:
            self.focus_in = False
            return super().focusInEvent(event)


def create_tool_bar(instance):
    tool_bar = QToolBar('Actions')

    # Add/Remove Panels
    new_panel_widget = QWidget()
    new_panel_layout = QHBoxLayout()
    new_panel_btn = QPushButton('+')
    new_panel_btn.setFixedSize(20, 20)
    new_panel_sel = CustomAddComboBox(instance)
    new_panel_layout.addWidget(new_panel_btn)
    new_panel_layout.addWidget(new_panel_sel)
    new_panel_widget.setLayout(new_panel_layout)
    new_panel_action = QWidgetAction(instance)
    new_panel_action.setDefaultWidget(new_panel_widget)
    new_panel_action.setStatusTip('Add New Panel')
    new_panel_btn.clicked.connect(instance.setup_login)

    pop_panel_widget = QWidget()
    pop_panel_layout = QHBoxLayout()
    pop_panel_btn = QPushButton('-')
    pop_panel_btn.setFixedSize(20, 20)
    pop_panel_sel = CustomRemoveComboBox(instance)
    pop_panel_layout.addWidget(pop_panel_btn)
    pop_panel_layout.addWidget(pop_panel_sel)
    pop_panel_widget.setLayout(pop_panel_layout)
    pop_panel_action = QWidgetAction(instance)
    pop_panel_action.setDefaultWidget(pop_panel_widget)
    pop_panel_action.setStatusTip('Remove Panel')
    pop_panel_btn.clicked.connect(instance.pop_splitter_panel)

    # Start/Stop/Show/Hide Transfers
    # TODO: Connecting instance.executor signals for finishing
    start_transfers_action = QWidgetAction(instance)
    start_transfers_btn = QPushButton()
    start_transfers_btn.clicked.connect(instance.executor.start)
    start_transfers_btn.clicked.connect(
        partial(start_transfers_btn.setFlat, True)
    )
    start_transfers_btn.clicked.connect(
        partial(start_transfers_btn.setEnabled, False)
    )
    icon = QApplication.style().standardIcon(QStyle.SP_MediaPlay)
    start_transfers_btn.setIcon(icon)
    start_transfers_action.setDefaultWidget(start_transfers_btn)
    start_transfers_btn.setFixedSize(20, 20)

    stop_transfers_action = QWidgetAction(instance)
    stop_transfers_btn = QPushButton()
    start_transfers_btn.clicked.connect(
        partial(stop_transfers_btn.setFlat, False)
    )
    start_transfers_btn.clicked.connect(
        # TODO: Make this is a connected signal from executor
        partial(stop_transfers_btn.setEnabled, True)
    )
    stop_transfers_btn.clicked.connect(
        partial(stop_transfers_btn.setFlat, True)
    )
    stop_transfers_btn.clicked.connect(
        partial(stop_transfers_btn.setEnabled, False)
    )
    stop_transfers_btn.clicked.connect(
        partial(start_transfers_btn.setFlat, False)
    )
    stop_transfers_btn.clicked.connect(
        partial(start_transfers_btn.setEnabled, True)
    )
    icon = QApplication.style().standardIcon(QStyle.SP_MediaStop)
    stop_transfers_btn.setIcon(icon)
    stop_transfers_btn.setFixedSize(20, 20)
    stop_transfers_btn.setEnabled(False)
    stop_transfers_btn.setFlat(True)
    stop_transfers_action.setDefaultWidget(stop_transfers_btn)

    # Executor btn connections
    instance.executor.completed.connect(
        partial(start_transfers_btn.setFlat, False)
    )
    instance.executor.completed.connect(
        partial(start_transfers_btn.setEnabled, True)
    )
    instance.executor.completed.connect(
        partial(stop_transfers_btn.setFlat, True)
    )
    instance.executor.completed.connect(
        partial(stop_transfers_btn.setEnabled, False)
    )

    toggle_transfers_view_action = QWidgetAction(instance)
    toggle_transfers_view_btn = QPushButton()
    toggle_transfers_view_btn.clicked.connect(instance.toggle_transfer_window)
    icon = QApplication.style().standardIcon(QStyle.SP_FileDialogListView)
    toggle_transfers_view_btn.setIcon(icon)
    toggle_transfers_view_btn.setFixedSize(20, 20)
    toggle_transfers_view_action.setDefaultWidget(toggle_transfers_view_btn)

    tool_bar.addAction(new_panel_action)
    tool_bar.addAction(pop_panel_action)
    tool_bar.addSeparator()
    tool_bar.addAction(start_transfers_action)
    tool_bar.addAction(stop_transfers_action)
    tool_bar.addAction(toggle_transfers_view_action)
    return tool_bar
