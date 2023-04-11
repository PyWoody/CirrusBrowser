import os

from functools import partial

from cirrus import settings

from PySide6.QtCore import Slot
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QMenu, QToolButton


class BackNavigationButton(QToolButton):

    def __init__(self, parent):
        super().__init__(parent)
        self.setAutoRaise(True)
        self.setPopupMode(QToolButton.DelayedPopup)
        self.setIcon(
            QIcon(os.path.join(settings.ICON_DIR, 'page-left.svg'))
        )
        self.setMenu(NavigationMenu(parent))


class ForwardNavigationButton(QToolButton):

    def __init__(self, parent):
        super().__init__(parent)
        self.setAutoRaise(True)
        self.setPopupMode(QToolButton.DelayedPopup)
        self.setIcon(
            QIcon(os.path.join(settings.ICON_DIR, 'page-right.svg'))
        )
        self.setMenu(NavigationMenu(parent))


class NavigationMenu(QMenu):

    def __init__(self, parent):
        super().__init__(parent)

    @Slot(list)
    def build_menu(self, history):
        self.clear()
        processed = set()
        history.reverse()
        for location in history:
            if location not in processed:
                action = QAction(location, self)
                action.triggered.connect(
                    partial(self.parent().update_location_bar, location)
                )
                self.addAction(action)
                processed.add(location)
