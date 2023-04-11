from functools import partial

import boto3
import keyring

from cirrus import settings
from cirrus.items import DigitalOceanItem, S3Item
from cirrus.utils import HLine

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QStackedLayout,
    QVBoxLayout,
    QWidget,
)

# TODO: CTRL+CLICK to setup multiple splitter panels at login
# TODO: Style


class LoginWindow(QDialog):
    account_selected = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Add Account')
        self.accounts = []
        self.resize(300, 200)
        self.stack = QStackedLayout()
        self.s3_login = self.setup_s3_login()
        self.do_login = self.setup_do_login()
        self.dropbox_login = self.setup_dropbox_login()
        self.ssh_login = self.setup_ssh_login()
        self.landing_page = self.setup_landing_page()
        self.stack.addWidget(self.landing_page)
        self.stack.addWidget(self.setup_new_accounts())
        self.stack.addWidget(self.s3_login)
        self.stack.addWidget(self.do_login)
        self.stack.addWidget(self.dropbox_login)
        self.stack.addWidget(self.ssh_login)
        layout = QVBoxLayout()
        layout.addLayout(self.stack)
        self.setLayout(layout)

    def setup_landing_page(self):
        widget = QWidget()
        layout = QVBoxLayout()
        layout.addStretch(1)
        if users := list(settings.saved_users()):
            for user in users:
                account_selection = AccountLabel(user)
                account_selection.clicked.connect(
                    partial(self.accounts.append, user)
                )
                account_selection.clicked.connect(self.close)
                layout.addWidget(account_selection)
        layout.addWidget(HLine())
        new_account_label = QLabel('<strong>Add New Account</strong>')
        new_account_label.setAlignment(Qt.AlignHCenter)
        layout.addWidget(new_account_label)
        services = [
            ('&Amazon S3', self.s3_login),
            ('Digital &Ocean', self.do_login),
            ('&DropBox (Not Implemented)', self.dropbox_login),
            ('&SSH (Not Implemented)', self.ssh_login),
        ]
        for service, service_widget in services:
            btn = QPushButton(service)
            btn.setMinimumHeight(35)
            btn.setStyleSheet('text-align: left; padding-left: 30px;')
            btn.clicked.connect(
                partial(self.stack.setCurrentWidget, service_widget)
            )
            layout.addWidget(btn)
        btn = QPushButton('&Cancel')
        btn.setMinimumHeight(35)
        btn.clicked.connect(self.close)
        layout.addWidget(btn)
        layout.addStretch(1)
        widget.setLayout(layout)
        return widget

    def setup_new_accounts(self):
        # NOTE: Could make this into classes that emit clicked
        #       for stack change. This would allow class based
        #       region edits for setFocus
        widget = QWidget()
        layout = QVBoxLayout()
        username_edit = QLineEdit()
        password_edit = QLineEdit()
        password_edit.setEchoMode(QLineEdit.Password)
        form = QFormLayout()
        form.addRow('Username', username_edit)
        form.addRow('Password', password_edit)
        layout.addLayout(form)
        btn_layout = QHBoxLayout()
        ok_btn = QPushButton('OK')
        cancel_btn = QPushButton('&Cancel')
        cancel_btn.clicked.connect(
            partial(self.stack.setCurrentWidget, self.landing_page)
        )
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)
        widget.setLayout(layout)
        return widget

    def setup_s3_login(self, nickname='Amazon S3'):
        widget = QWidget()
        layout = QVBoxLayout()
        nickname_edit = QLineEdit(nickname)
        region_edit = QLineEdit()
        root_edit = QLineEdit()
        root_updater = root_handler(root_edit)
        root_edit.textChanged.connect(root_updater)
        key_edit = QLineEdit()
        secret_key_edit = QLineEdit()
        secret_key_edit.setEchoMode(QLineEdit.Password)
        form = QFormLayout()
        form.addRow('Nickname', nickname_edit)
        form.addRow('Region &Name', region_edit)
        form.addRow('&Root', root_edit)
        form.addRow('&Acecss Key', key_edit)
        form.addRow('&Secret Access Key*', secret_key_edit)
        btn_layout = QVBoxLayout()
        login_btn = QPushButton('&Login')
        login_btn.setMinimumHeight(35)
        login_partial = partial(
            self.test_s3_credentials,
            'Amazon S3',
            nickname_edit,
            region_edit,
            root_edit,
            key_edit,
            secret_key_edit,
        )
        login_btn.clicked.connect(login_partial)
        region_edit.returnPressed.connect(login_partial)
        key_edit.returnPressed.connect(login_partial)
        secret_key_edit.returnPressed.connect(login_partial)
        cancel_btn = QPushButton('&Cancel')
        cancel_btn.setMinimumHeight(35)
        cancel_btn.clicked.connect(partial(self.stack.setCurrentIndex, 0))
        btn_layout.addWidget(login_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(form)
        layout.addLayout(btn_layout)
        widget.setLayout(layout)
        return widget

    def setup_do_login(self, nickname='Digital Ocean'):
        widget = QWidget()
        layout = QVBoxLayout()
        nickname_edit = QLineEdit(nickname)
        region_edit = QLineEdit()
        region_edit.setPlaceholderText('e.g, sfo2, nyc3')
        endpoint_edit = QLineEdit()
        root_edit = QLineEdit()
        root_updater = root_handler(root_edit)
        root_edit.textChanged.connect(root_updater)
        endpoint_updater = endpoint_handler(
            endpoint_edit, 'https://{0}.digitaloceanspaces.com'
        )
        region_edit.textChanged.connect(endpoint_updater)
        key_edit = QLineEdit()
        secret_key_edit = QLineEdit()
        secret_key_edit.setEchoMode(QLineEdit.Password)
        form = QFormLayout()
        form.addRow('Nickname', nickname_edit)
        form.addRow('Region &Name', region_edit)
        form.addRow('&Endpoint URL', endpoint_edit)
        form.addRow('&Root', root_edit)
        form.addRow('&Acecss Key', key_edit)
        form.addRow('&Secret Access Key', secret_key_edit)
        btn_layout = QVBoxLayout()
        login_btn = QPushButton('&Login')
        login_btn.setMinimumHeight(35)
        login_partial = partial(
            self.test_do_credentials,
            'Digital Ocean',
            nickname_edit,
            region_edit,
            endpoint_edit,
            root_edit,
            key_edit,
            secret_key_edit,
        )
        login_btn.clicked.connect(login_partial)
        region_edit.returnPressed.connect(login_partial)
        endpoint_edit.returnPressed.connect(login_partial)
        root_edit.returnPressed.connect(login_partial)
        key_edit.returnPressed.connect(login_partial)
        secret_key_edit.returnPressed.connect(login_partial)
        cancel_btn = QPushButton('&Cancel')
        cancel_btn.setMinimumHeight(35)
        cancel_btn.clicked.connect(partial(self.stack.setCurrentIndex, 0))
        btn_layout.addWidget(login_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(form)
        layout.addLayout(btn_layout)
        widget.setLayout(layout)
        return widget

    def setup_ssh_login(self):
        widget = QWidget()
        layout = QVBoxLayout()
        layout.addWidget(QLabel('Not implemented.'))
        cancel_btn = QPushButton('&Cancel')
        cancel_btn.setMinimumHeight(35)
        cancel_btn.clicked.connect(partial(self.stack.setCurrentIndex, 0))
        layout.addWidget(cancel_btn)
        widget.setLayout(layout)
        return widget

    def setup_dropbox_login(self):
        widget = QWidget()
        layout = QVBoxLayout()
        layout.addWidget(QLabel('Not implemented.'))
        cancel_btn = QPushButton('&Cancel')
        cancel_btn.setMinimumHeight(35)
        cancel_btn.clicked.connect(partial(self.stack.setCurrentIndex, 0))
        layout.addWidget(cancel_btn)
        widget.setLayout(layout)
        return widget

    def test_do_credentials(
            self,
            service_type,
            nickname,
            region_name,
            endpoint_url,
            root,
            key,
            secret_key,
    ):
        nickname = nickname.text()
        region = region_name.text()
        endpoint = endpoint_url.text()
        root = root.text()
        key = key.text()
        secret_key = secret_key.text()
        try:
            user = settings.new_user(
                act_type=service_type,
                access_key=key,
                nickname=nickname,
                region=region,
                endpoint_url=endpoint,
                root=root,
            )
            session = boto3.session.Session()
            client = session.client(
                's3',
                region_name=region,
                endpoint_url=endpoint,
                aws_access_key_id=key,
                aws_secret_access_key=secret_key,
            )
            item = DigitalOceanItem(user, is_dir=True)
            config = {
                'Bucket': item.bucket,
                'MaxKeys': 1_000,
                'Delimiter': '/',
            }
            if item.space:
                config['Prefix'] = item.space
            _ = client.list_objects_v2(**config)
        except ValueError as e:
            # Alert
            msg = f'<b>Error:</b> {str(e)}'
            msg += '\n'
            msg += '<b>Information Receieved:</b>'
            msg += '\n\t'
            msg += f'<b>region_name:</b> {region}'
            msg += '\n\t'
            msg += f'<b>endpoint_url:</b> {endpoint}'
            msg += '\n\t'
            msg += f'<b>root:</b> {root}'
            msg += '\n\t'
            msg += f'<b>aws_access_key_id:</b> {key}'
            msg += '\n\t'
            msg += '<b>aws_secret_access_key_id:</b> (protected)'
            msg += '\n'
            QMessageBox.critical(
                self,
                'Digitial Ocean Client Error',
                msg,
                defaultButton=QMessageBox.NoButton,
            )
        else:
            # Keyring
            settings.update_saved_users(user)
            keyring.set_password('system', f'_s3_{key}_secret_key', secret_key)
            self.accounts.append(user)
            self.close()

    def test_s3_credentials(
            self,
            service_type,
            nickname,
            region_name,
            root,
            key,
            secret_key,
    ):
        nickname = nickname.text()
        region = region_name.text()
        root = root.text()
        key = key.text()
        secret_key = secret_key.text()
        try:
            user = settings.new_user(
                act_type=service_type,
                access_key=key,
                nickname=nickname,
                region=region,
                root=root,
            )
            session = boto3.session.Session()
            client = session.client(
                's3',
                region_name=region,
                aws_access_key_id=key,
                aws_secret_access_key=secret_key,
            )
            item = S3Item(user, is_dir=True)
            config = {
                'Bucket': item.bucket,
                'MaxKeys': 1_000,
                'Delimiter': '/',
            }
            if item.space:
                config['Prefix'] = item.space
            _ = client.list_objects_v2(**config)
        except ValueError as e:
            # Alert
            msg = f'<b>Error:</b> {str(e)}'
            msg += '\n'
            msg += '<b>Information Receieved:</b>'
            msg += '\n\t'
            msg += f'<b>region_name:</b> {region}'
            msg += '\n\t'
            msg += f'<b>root:</b> {root}'
            msg += '\n\t'
            msg += f'<b>aws_access_key_id:</b> {key}'
            msg += '\n\t'
            msg += '<b>aws_secret_access_key_id:</b> (protected)'
            msg += '\n'
            QMessageBox.critical(
                self,
                'S3 Client Error',
                msg,
                defaultButton=QMessageBox.NoButton,
            )
        else:
            # Keyring
            settings.update_saved_users(user)
            keyring.set_password('system', f'_s3_{key}_secret_key', secret_key)
            self.accounts.append(user)
            self.close()

    def closeEvent(self, *args, **kwargs):
        self.account_selected.emit(self.accounts)
        return super().closeEvent(*args, **kwargs)


class AccountLabel(QLabel):
    clicked = Signal()

    def __init__(self, account, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.setFrameShape(QFrame.Panel)
        self.setFrameShadow(QFrame.Raised)
        self.setTextInteractionFlags(
            Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard
        )
        self.setTextFormat(Qt.RichText)
        self.setText(
            '\n'.join(
                f'<div><b>{k}:</b> {v}</div>' for k, v in account.items() if v
            )
        )

    def mousePressEvent(self, event):
        if not self.frameShadow() == QFrame.Sunken:
            self.setFrameShadow(QFrame.Sunken)
        return super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if self.hasSelectedText():
            # Allows for copying-and-pasting w/o selecting
            return super().mouseReleaseEvent(event)
        if not self.frameShadow() == QFrame.Plain:
            self.setFrameShadow(QFrame.Plain)
        self.clicked.emit()


def root_handler(label):
    def updater(text):
        if not text.startswith('/'):
            label.setText(f'/{text}')
    return updater


def endpoint_handler(label, url):
    def updater(text):
        label.setText(url.format(text))
    return updater


if __name__ == '__main__':
    import sys
    from PySide6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    window = LoginWindow()
    window.show()
    sys.exit(app.exec())
