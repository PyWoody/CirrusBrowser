from cirrus import toolbars
from cirrus.views import (
    DigitalOceanFileListingView,
    LocalFileListingView,
    S3FileListingView,
)

from PySide6.QtWidgets import QVBoxLayout, QWidget


class DigitOceanFileListingWindow(QWidget):

    def __init__(self, user, parent=None):
        super().__init__(parent)
        self.view = DigitalOceanFileListingView(user)
        self.location_bar = self.view.create_navigation_bar()
        self.info_bar = self.view.create_info_bar()
        layout = QVBoxLayout()
        layout.addLayout(self.location_bar)
        layout.addWidget(self.view)
        layout.addWidget(self.info_bar)
        self.setLayout(layout)


class LocalFileListingWindow(QWidget):

    def __init__(self, user, parent=None):
        super().__init__(parent)
        self.view = LocalFileListingView(user)
        self.location_bar = self.view.create_navigation_bar()
        self.info_bar = self.view.create_info_bar()
        layout = QVBoxLayout()
        layout.addLayout(self.location_bar)
        layout.addWidget(self.view)
        layout.addWidget(self.info_bar)
        self.setLayout(layout)


class S3FileListingWindow(QWidget):

    def __init__(self, user, parent=None):
        super().__init__(parent)
        self.view = S3FileListingView(user)
        self.location_bar = self.view.create_navigation_bar()
        self.info_bar = self.view.create_info_bar()
        layout = QVBoxLayout()
        layout.addLayout(self.location_bar)
        layout.addWidget(self.view)
        layout.addWidget(self.info_bar)
        self.setLayout(layout)
