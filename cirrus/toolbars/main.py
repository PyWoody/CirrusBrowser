from functools import partial
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


def create_tool_bar(instance):
    new_panel_sel = None
    pop_panel_sel = None

    def add_drop_down(activate_index):
        print(activate_index)
        # NOTE: This doesn't make sense but it's OK for now
        #       New panels will come from settings, not existing panels
        #       This is really for removing a panel
        if activate_index != 0:
            for index in range(1, new_panel_sel.count() + 1):
                new_panel_sel.removeItem(index)
            for _, account in instance.splitter_listing_panels:
                new_panel_sel.addItem(
                    f'{account["Type"]} - {account["Root"]}'
                )

    def remove_dropdown():
        if pop_panel_sel is not None:
            pop_panel_sel.deleteLater()
            pop_panel_sel = None
        pop_panel_sel = QComboBox('⌄')
        pop_panel_sel.activated.conect(
            partial, print, 'REMOVED:',
        )
        for _, account in instance.splitter_listing_panels:
            pop_panel_sel.addItem(
                f'{account["Type"]} - {account["Root"]}'
            )
        return pop_panel_sel

    tool_bar = QToolBar('Actions')

    # Add/Remove Panels
    new_panel_widget = QWidget()
    new_panel_layout = QHBoxLayout()
    new_panel_btn = QPushButton('+')
    new_panel_btn.setFixedSize(20, 20)
    new_panel_sel = QComboBox()
    new_panel_sel.setPlaceholderText('⌄')
    # new_panel_sel.setCurrentIndex(-1)
    # new_panel_sel.activated.connect(add_drop_down)
    new_panel_sel.addItem('Test')
    new_panel_sel.activated.connect(partial(print, 'HERE'))
    new_panel_layout.addWidget(new_panel_btn)
    new_panel_layout.addWidget(new_panel_sel)
    new_panel_widget.setLayout(new_panel_layout)
    new_panel_action = QWidgetAction(instance)
    new_panel_action.setDefaultWidget(new_panel_widget)
    new_panel_action.setStatusTip('Add New Panel')
    new_panel_btn.clicked.connect(instance.setup_login)

    pop_panel_btn = QPushButton('-')
    pop_panel_btn.setFixedSize(20, 20)
    pop_panel_action = QWidgetAction(instance)
    pop_panel_action.setDefaultWidget(pop_panel_btn)
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
