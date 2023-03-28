from functools import partial

from cirrus import utils
from cirrus.validators import LocalPathValidator

from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QStyle,
    QToolBar,
    QWidget,
    QWidgetAction,
)


def create_navigation_bar(view):
    # TODO: <, >, Refresh  (Icons)
    back_btn = QPushButton()
    icon = QApplication.style().standardIcon(QStyle.SP_ArrowBack)
    back_btn.setIcon(icon)
    back_btn.clicked.connect(partial(print, 'back'))
    back_btn.setFixedSize(20, 20)
    back_btn.setEnabled(False)
    back_btn.setFlat(True)
    forward_btn = QPushButton()
    icon = QApplication.style().standardIcon(QStyle.SP_ArrowForward)
    forward_btn.setIcon(icon)
    forward_btn.clicked.connect(partial(print, 'forward'))
    forward_btn.setFixedSize(20, 20)
    forward_btn.setEnabled(False)
    forward_btn.setFlat(True)
    refresh_btn = QPushButton()
    icon = QApplication.style().standardIcon(QStyle.SP_BrowserReload)
    refresh_btn.setIcon(icon)
    refresh_btn.clicked.connect(view.refresh)
    refresh_btn.setFixedSize(20, 20)
    refresh_btn.setFlat(True)
    # TODO: Will become a QComboBox w/ histories
    view.location_bar = QLineEdit()
    # TODO: S3 Validators
    if view.type.lower() == 'local':
        view.location_bar.setValidator(LocalPathValidator())
    view.location_bar.insert(view.root)
    view.location_bar.editingFinished.connect(view.change_dir)
    view.location_bar_change.connect(view.update_location_bar)
    window_location_bar_layout = QHBoxLayout()
    window_location_bar_layout.addWidget(back_btn)
    window_location_bar_layout.addWidget(forward_btn)
    window_location_bar_layout.addWidget(refresh_btn)
    window_location_bar_layout.addWidget(utils.VLine())
    window_location_bar_layout.addWidget(view.location_bar)
    return window_location_bar_layout


def create_info_bar(view):
    view.info_bar = QLabel()
    view.info_bar_change.connect(view.update_info_bar)
    return view.info_bar
