from cirrus.views import (
    DigitalOceanFileListingView,
    LocalFileListingView,
    S3FileListingView,
)

from PySide6.QtCore import Slot
from PySide6.QtWidgets import QVBoxLayout, QWidget


class BaseListingWindow(QWidget):

    @Slot(str)
    def handle_root_changes(self, root):
        if self.from_nav_btn:
            self.from_nav_btn = False
            return
        self.current_index += 1
        self.history = self.history[:self.current_index]
        self.history.append(root)
        self.view.location_bar.set_model(self.history)
        if not self.view.back_btn.isEnabled():
            self.view.back_btn.setEnabled(True)
        if self.view.forward_btn.isEnabled():
            self.view.forward_btn.setEnabled(False)

    @Slot()
    def back(self):
        self.from_nav_btn = True
        self.current_index -= 1
        location = self.history[self.current_index]
        if self.current_index == 0:
            self.view.back_btn.setEnabled(False)
        if not self.view.forward_btn.isEnabled():
            self.view.forward_btn.setEnabled(True)
        self.view.update_location_bar(location)

    @Slot()
    def back_option(self):
        self.view.back_btn.menu().build_menu(
            self.history[:self.current_index]
        )

    @Slot()
    def forward(self):
        self.from_nav_btn = True
        self.current_index += 1
        location = self.history[self.current_index]
        if self.current_index == (len(self.history) - 1):
            self.view.forward_btn.setEnabled(False)
        if not self.view.back_btn.isEnabled():
            self.view.back_btn.setEnabled(True)
        self.view.update_location_bar(location)

    @Slot()
    def forward_option(self):
        self.view.forward_btn.menu().build_menu(
            self.history[self.current_index:]
        )


class DigitOceanFileListingWindow(BaseListingWindow):

    # TODO: Kill fetch_children's on back/forward butto presses
    def __init__(self, client, parent=None):
        super().__init__(parent)
        self.from_nav_btn = False
        self.current_index = 0
        self.history = []
        self.view = DigitalOceanFileListingView(client)
        self.location_bar = self.view.create_navigation_bar()
        self.info_bar = self.view.create_info_bar()
        layout = QVBoxLayout()
        layout.addLayout(self.location_bar)
        layout.addWidget(self.view)
        layout.addWidget(self.info_bar)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        self.view.location_bar.set_model(self.history)
        self.view.location_bar.selection_made.connect(
            self.view.update_location_bar
        )

        self.view.root_changed.connect(self.handle_root_changes)
        self.view.back_btn.clicked.connect(self.back)
        self.view.forward_btn.clicked.connect(self.forward)
        self.history.append(self.view.location_bar.text())


class LocalFileListingWindow(BaseListingWindow):

    def __init__(self, client, parent=None):
        super().__init__(parent)
        self.from_nav_btn = False
        self.current_index = 0
        self.history = []
        self.view = LocalFileListingView(client)
        self.location_bar_layout = self.view.create_navigation_bar()
        self.info_bar = self.view.create_info_bar()
        layout = QVBoxLayout()
        layout.addLayout(self.location_bar_layout)
        layout.addWidget(self.view)
        layout.addWidget(self.info_bar)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        self.view.location_bar.set_model(self.history)
        self.view.location_bar.selection_made.connect(
            self.view.update_location_bar
        )

        self.view.root_changed.connect(self.handle_root_changes)
        self.view.back_btn.clicked.connect(self.back)
        self.view.back_btn.menu().aboutToShow.connect(self.back_option)
        self.view.forward_btn.clicked.connect(self.forward)
        self.view.forward_btn.menu().aboutToShow.connect(self.forward_option)
        self.history.append(self.view.location_bar.text())


class S3FileListingWindow(BaseListingWindow):

    def __init__(self, client, parent=None):
        super().__init__(parent)
        self.from_nav_btn = False
        self.current_index = 0
        self.history = []
        self.view = S3FileListingView(client)
        self.location_bar = self.view.create_navigation_bar()
        self.info_bar = self.view.create_info_bar()
        layout = QVBoxLayout()
        layout.addLayout(self.location_bar)
        layout.addWidget(self.view)
        layout.addWidget(self.info_bar)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        self.view.location_bar.set_model(self.history)
        self.view.location_bar.selection_made.connect(
            self.view.update_location_bar
        )

        self.view.root_changed.connect(self.handle_root_changes)
        self.view.back_btn.clicked.connect(self.back)
        self.view.forward_btn.clicked.connect(self.forward)
        self.history.append(self.view.location_bar.text())
