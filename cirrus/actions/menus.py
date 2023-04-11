import os

from functools import partial

from cirrus import settings

from PySide6.QtCore import Slot
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QMenu, QToolButton


class AddPanelToolButton(QToolButton):

    def __init__(self, parent):
        super().__init__(parent)
        self.setPopupMode(QToolButton.MenuButtonPopup)
        self.setDefaultAction(AddPanelDefaultAction(parent))
        self.setMenu(AddPanelOptionMenu(parent))


class AddPanelDefaultAction(QAction):

    def __init__(self, parent):
        super().__init__(parent)
        self.setIcon(QIcon(os.path.join(settings.ICON_DIR, 'plus.svg')))
        self.setToolTip('Add New Panel')
        self.setStatusTip('Opens the Add New Panel dialog.')
        self.triggered.connect(self.process)

    @Slot(bool)
    def process(self, checked):
        self.parent().setup_login()


class AddPanelOptionMenu(QMenu):

    def __init__(self, parent):
        super().__init__(parent)
        self.aboutToShow.connect(self.build_menu)

    @Slot()
    def build_menu(self):
        self.clear()
        for account in settings.saved_users():
            text = f'({account["Type"]}) {account["Root"]}'
            action = QAction(text, self)
            action.triggered.connect(partial(self.process, account))
            action.setStatusTip(f'Add {text} panel.')
            self.addAction(action)

    @Slot(dict)
    def process(self, account):
        self.parent().add_splitter_panel(account)


class RemovePanelToolButton(QToolButton):

    def __init__(self, parent):
        super().__init__(parent)
        self.setPopupMode(QToolButton.MenuButtonPopup)
        self.setDefaultAction(RemovePanelDefaultAction(parent))
        self.setMenu(RemovePanelOptionMenu(parent))


class RemovePanelDefaultAction(QAction):

    def __init__(self, parent):
        super().__init__(parent)
        self.setIcon(QIcon(os.path.join(settings.ICON_DIR, 'minus.svg')))
        self.setToolTip('Remove Last Panel')
        self.setStatusTip('Removes the Last Panel from the window.')
        self.hovered.connect(self.update_tool_tip)
        self.triggered.connect(self.process)

    @Slot()
    def update_tool_tip(self):
        _, account = self.parent().splitter_listing_panels[-1]
        self.setToolTip(f'Remove ({account["Type"]}) {account["Root"]}')

    @Slot(bool)
    def process(self, checked):
        self.parent().pop_splitter_panel()


class RemovePanelOptionMenu(QMenu):

    def __init__(self, parent):
        super().__init__(parent)
        self.aboutToShow.connect(self.build_menu)

    @Slot()
    def build_menu(self):
        self.clear()
        for index, account in enumerate(settings.saved_panels()):
            text = f'({account["Type"]}) {account["Root"]}'
            action = QAction(text, self)
            action.triggered.connect(partial(self.process, index))
            action.setStatusTip(f'Remove {text} panel.')
            self.addAction(action)

    @Slot(int)
    def process(self, index):
        self.parent().remove_splitter_panel(index)


class ToggleProcessingTransfers(QAction):
    
    def __init__(self, parent):
        super().__init__(parent)
        self.setIcon(
            QIcon(os.path.join(settings.ICON_DIR, 'data-transfer-both.svg'))
        )
        self.setCheckable(True)
        self.setToolTip('Start Transfers')
        self.setStatusTip('Start all pending Transfers')
        self.triggered.connect(self.toggle)

    @Slot(bool)
    def toggle(self, checked):
        if checked:
            self.parent().executor.start()
            self.setToolTip('Stop Transfers')
            self.setStatusTip('Stop all running and pending transfers.')
        else:
            self.parent().executor.stop()
            self.setToolTip('Start Transfers')
            self.setStatusTip('Start all pending Transfers')


class ToggleTransferPanel(QAction):
    
    def __init__(self, parent):
        super().__init__(parent)
        self.setCheckable(True)
        if settings.transfer_window_visible():
            self.setChecked(True)
            self.setIcon(
                QIcon(os.path.join(settings.ICON_DIR, 'eye-empty.svg'))
            )
            self.setToolTip('Hide Transfers')
            self.setStatusTip('Hide the Transfers, Errors, and Completed window.')
        else:
            self.setIcon(
                QIcon(os.path.join(settings.ICON_DIR, 'eye-off.svg'))
            )
            self.setToolTip('Show Transfers')
            self.setStatusTip('Show the Transfers, Errors, and Completed window.')
        self.triggered.connect(self.toggle)

    @Slot(bool)
    def toggle(self, checked):
        settings.update_transfer_window_status(checked)
        if checked:
            self.parent().transfers_window.show()
            self.setIcon(
                QIcon(os.path.join(settings.ICON_DIR, 'eye-empty.svg'))
            )
            self.setToolTip('Hide Transfers')
            self.setStatusTip('Hide the Transfers, Errors, and Completed window.')
        else:
            self.parent().transfers_window.hide()
            self.setIcon(
                QIcon(os.path.join(settings.ICON_DIR, 'eye-off.svg'))
            )
            self.setToolTip('Show Transfers')
            self.setStatusTip('Show the Transfers, Errors, and Completed window.')
