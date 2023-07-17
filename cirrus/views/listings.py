import logging
import os

from functools import partial

from cirrus import actions, items, settings, utils
from cirrus.items import LocalItem
from cirrus.models import (
    DigitalOceanFilesTreeModel,
    LocalFileSystemModel,
    S3FilesTreeModel,
)
from cirrus.widgets import NavBarLineEdit
from cirrus.validators import LocalPathValidator

from PySide6.QtCore import (
    Qt,
    QDir,
    QItemSelection,
    QMimeData,
    QModelIndex,
    QPoint,
    QThreadPool,
    Signal,
    Slot,
)
from PySide6.QtGui import (
    QIcon,
    QDrag,
    QDragMoveEvent,
    QDropEvent,
    QMouseEvent,
)
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTreeView,
)


# TODO: Move away from selectedIndexes. Manually track instead


class FileListingTreeView(QTreeView):
    info_bar_change = Signal(str)
    location_bar_change = Signal(str)
    location_index_change = Signal(int)
    root_changed = Signal(str)
    context_selections = Signal(object, object,  list, list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setExpandsOnDoubleClick(False)
        self.setUniformRowHeights(True)
        self.setAnimated(False)
        self.setSortingEnabled(True)
        self.setTextElideMode(Qt.ElideMiddle)
        self.setIndentation(10)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)

    def setup_header(self):
        # name | type | size | last mod
        # (Optional) in the S3 subclass
        # created | permissions (ACL)
        header = QHeaderView(Qt.Horizontal)
        self.setHeader(header)
        header.setSectionsMovable(True)
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSortIndicator(0, Qt.AscendingOrder)
        self.resizeColumnToContents(0)
        self.resizeColumnToContents(1)
        self.resizeColumnToContents(2)

    @Slot(Qt.DropActions)
    def startDrag(self, actions):
        if indexes := self.selectedIndexes():
            drag = QDrag(self)
            drag.setMimeData(self.model().mimeData(indexes))
            _ = drag.exec(Qt.CopyAction | Qt.MoveAction, Qt.CopyAction)

    @Slot(QDragMoveEvent)
    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    @Slot(QDropEvent)
    def dropEvent(self, event):
        # event == originator
        # self == destination (Always QFileSystemModel)
        if self is event.source():
            print('Not implemented yet')
            event.ignore()
            return
        if urls := event.mimeData().urls():
            dest_index = self.indexAt(event.pos())
            if dest_index.isValid():
                dest_parent = dest_index.parent()
                if dest_parent.isValid():
                    dest_parents = []
                    while dest_parent.isValid():
                        if (data := dest_parent.data()) != os.sep:
                            dest_parents.append(data)
                        dest_parent = dest_parent.parent()
                    dest_path = os.sep + os.sep.join(dest_parents[::-1])
                    if self.model().isDir(dest_index):
                        dest_path = os.path.join(dest_path, dest_index.data())
                else:
                    dest_path = os.path.join(self.root, dest_index.data())
                destination = items.account_to_item(
                    items.new_user(self.user, dest_path), is_dir=True
                )
            else:
                destination = items.account_to_item(
                    items.new_user(self.user, self.root), is_dir=True
                )
            source_type = items.types[event.source().type.lower()]
            model = event.source().model()
            files = []
            folders = []
            for url in urls:
                url_model_index = model.index(url.path(), 0)
                if url_model_index.isValid():
                    account = items.new_user(self.user, url.path())
                    if model.isDir(url_model_index):
                        folders.append(
                            items.account_to_item(account, is_dir=True)
                        )
                    else:
                        file_info = model.fileInfo(url_model_index)
                        item = source_type(
                            account,
                            size=file_info.size(),
                            ctime=utils.date.qdatetime_to_iso(
                                file_info.birthTime()
                            ),
                            mtime= utils.date.qdatetime_to_iso(
                                file_info.lastModified()
                            )
                        )
                        files.append(item)
                else:
                    logging.warn(f'Received invalid index for {url.path()}')
            if files and folders:
                action = actions.listings.QueueRecursiveItemsAction(
                    event.source(), files, folders, destination
                )
            elif files:
                action = actions.listings.QueueFilesAction(
                    event.source(), files, destination
                )
            elif folders:
                action = actions.listings.QueueFoldersAction(
                    event.source(), folders, destination
                )
            else:
                logging.warn(
                    f'Failed a dropEvent from {event().source()} to {self}'
                )
                event.ignore()
                return
            runnable = action.runnable()
            runnable.signals.aborted.connect(partial(print, 'Aborted!'))
            runnable.signals.update.connect(print)
            # runnable.signals.process_queue.connect(self.start_queue_tmp)
            runnable.signals.select.connect(
                self.parent().parent().parent().parent(
                    ).transfers_window.tabs.widget(0).model().select
            )
            runnable.signals.ss_callback.connect(utils.execute_ss_callback)
            runnable.signals.callback.connect(utils.execute_callback)
            runnable.signals.finished.connect(print)
            QThreadPool().globalInstance().start(runnable)
            event.acceptProposedAction()
        else:
            event.ignore()

    def create_navigation_bar(self):
        if self.location_bar is not None:
            cls_name = self.__class__.__name__
            raise Exception(f'location_bar already exists for {cls_name}.')
        self.back_btn = actions.navigation.BackNavigationButton(self)
        self.back_btn.setEnabled(False)
        self.forward_btn = actions.navigation.ForwardNavigationButton(self)
        self.forward_btn.setEnabled(False)
        refresh_btn = QPushButton()
        refresh_btn.setIcon(
            QIcon(os.path.join(settings.ICON_DIR, 'refresh.svg'))
        )
        refresh_btn.clicked.connect(self.refresh)
        refresh_btn.setFlat(True)
        self.location_bar = NavBarLineEdit(self)
        # TODO: S3 Validators
        if self.type.lower() == 'local':
            self.location_bar.setValidator(LocalPathValidator())
        self.location_bar.insert(self.root)
        self.location_bar.returnPressed.connect(self.change_dir)
        self.location_bar_change.connect(self.update_location_bar)
        window_location_bar_layout = QHBoxLayout()
        window_location_bar_layout.addWidget(self.back_btn)
        window_location_bar_layout.addWidget(self.forward_btn)
        window_location_bar_layout.addWidget(refresh_btn)
        window_location_bar_layout.addWidget(utils.VLine())
        window_location_bar_layout.addWidget(self.location_bar)
        return window_location_bar_layout

    def create_info_bar(self):
        if self.info_bar is not None:
            cls_name = self.__class__.__name__
            raise Exception(f'info_bar already exists {cls_name}.')
        self.info_bar = QLabel()
        self.info_bar_change.connect(self.update_info_bar)
        return self.info_bar

    def refresh(self):
        raise NotImplementedError('Must specificy refrresh() in a subclass')


class LocalFileListingView(FileListingTreeView):
    # TODO: Turn off auto updating. It's very slow

    def __init__(self, user, parent=None):
        super().__init__(parent)
        user = user.copy()
        if root := user.get('Root'):
            self.root = root
        else:
            self.root = os.path.expanduser('~')
        self.user = user
        self.location_bar = None
        self.info_bar = None
        model = LocalFileSystemModel()
        model.setFilter(
            QDir.AllEntries | QDir.NoDotAndDotDot | QDir.AllDirs | QDir.Hidden
        )
        model.setRootPath(self.root)
        self.setModel(model)
        self.setRootIndex(model.index(self.root))
        self.setup_header()
        self.doubleClicked.connect(self.item_double_clicked)

    @property
    def type(self):
        return 'local'

    @classmethod
    def clone(cls, user, parent):
        return cls(user, parent=parent)

    def refresh(self):
        model = LocalFileSystemModel()
        model.setFilter(
            QDir.AllEntries | QDir.NoDotAndDotDot | QDir.AllDirs | QDir.Hidden
        )
        model.setRootPath(self.root)
        prev_model = self.model()
        prev_selection_model = self.selectionModel()
        self.setModel(model)
        self.setRootIndex(model.index(self.root))
        if self.location_bar.text() != self.root:
            self.location_bar.clear()
            self.location_bar.insert(self.root)
        if prev_model:
            prev_model.deleteLater()
        if prev_selection_model:
            prev_selection_model.deleteLater()

    @Slot()
    def change_dir(self):
        if (location := self.location_bar.text()) != self.root:
            self.root = location
            self.user['Root'] = location
            self.root_changed.emit(location)
            self.refresh()

    @Slot(str)
    def update_location_bar(self, path):
        if os.path.isdir(path):
            self.location_bar.clear()
            self.location_bar.insert(path)
            self.change_dir()

    @Slot(str)
    def update_info_bar(self, status):
        self.info_bar.setText(status)

    def contextMenuEvent(self, event):
        files, folders = [], []
        for index in self.selectedIndexes():
            if index.column() == 0:
                if item := index.model().fileInfo(index):
                    _user = self.user.copy()
                    _user['Root'] = item.filePath()
                    if item.isFile():
                        standard_item = LocalItem(
                            _user, size=item.size()
                        )
                        files.append(standard_item)
                    else:
                        standard_item = LocalItem(
                            _user, is_dir=True
                        )
                        folders.append(standard_item)
        self.context_selections.emit(self, event.globalPos(), files, folders)

    @Slot(QModelIndex)
    def item_double_clicked(self, index):
        if item := index.model().fileInfo(index):
            if item.isDir():
                self.location_bar_change.emit(item.filePath())

    @Slot(QItemSelection, QItemSelection)
    def selectionChanged(self, selected, deselected):
        # files, folders will be lists for future proofing
        files, folders = [], []
        filesize_selected = 0
        for index in self.selectedIndexes():
            if index.column() == 0:
                if item := index.model().fileInfo(index):
                    if item.isFile():
                        files.append(item)
                        filesize_selected += item.size()
                    else:
                        folders.append(item)
        output = ''
        if files:
            filesize_selected = utils.files.bytes_to_human(filesize_selected)
            output += (f'{len(files):,} file{"s" if len(files) > 1 else ""} '
                       f'selected for {filesize_selected}')
            if folders:
                output += (f' and {len(folders):,} '
                           f'folder{"s" if len(folders) > 1 else ""} selected')
        elif folders:
            output += (f'{len(folders):,} '
                       f'folder{"s" if len(folders) > 1 else ""} selected')
        self.info_bar_change.emit(output)
        return super().selectionChanged(selected, deselected)


class BaseS3FileListingView(FileListingTreeView):
    # TODO: On-hover starting fetch_children w/ tracking for start/stop

    def __init__(self, parent=None):
        super().__init__(parent)
        self.location_bar = None
        self.info_bar = None
        self.user = None
        self.root = None

    @classmethod
    def clone(cls, user, parent):
        return cls(user, parent=parent)

    @Slot(QModelIndex)
    def item_double_clicked(self, index):
        if item := index.model().itemFromIndex(index):
            if data := item.data():
                if data.is_dir:
                    self.location_bar_change.emit(data.root)

    def contextMenuEvent(self, event):
        files, folders = [], []
        for index in self.selectedIndexes():
            if index.column() == 0:
                if item := index.model().itemFromIndex(index).data():
                    if item.is_dir:
                        folders.append(item)
                    else:
                        files.append(item)
        self.context_selections.emit(self, event.globalPos(), files, folders)

    @Slot(QItemSelection, QItemSelection)
    def selectionChanged(self, selected, deselected):
        # files, folders will be lists for future proofing
        files, folders = [], []
        filesize_selected = 0
        model = None
        for index in self.selectedIndexes():
            if index.column() == 0:
                if model is None:
                    model = index.model()
                if item := model.itemFromIndex(index):
                    if data := item.data():
                        if data.is_dir:
                            folders.append(item)
                        else:
                            files.append(data.key)
                            filesize_selected += data.size
        output = ''
        if files:
            filesize_selected = utils.files.bytes_to_human(filesize_selected)
            output += (f'{len(files):,} file{"s" if len(files) > 1 else ""} '
                       f'selected for {filesize_selected}')
            if folders:
                output += (f' and {len(folders):,} '
                           f'folder{"s" if len(folders) > 1 else ""} selected')
        elif folders:
            output += (f'{len(folders):,} '
                       f'folder{"s" if len(folders) > 1 else ""} selected')
        self.info_bar_change.emit(output)
        return super().selectionChanged(selected, deselected)

    @Slot()
    def change_dir(self):
        if (location := self.location_bar.text()) != self.root:
            self.root = location
            self.user['Root'] = location
            self.root_changed.emit(location)
            self.refresh()

    @Slot(str)
    def update_location_bar(self, root):
        self.location_bar.clear()
        self.location_bar.insert(root)
        self.change_dir()

    @Slot(str)
    def update_info_bar(self, status):
        self.info_bar.setText(status)


class S3FileListingView(BaseS3FileListingView):

    def __init__(self, user, parent=None):
        super().__init__(parent)
        user = user.copy()
        if not user['Root'].startswith('/'):
            user['Root'] = '/' + user['Root']
        self.root = user['Root']
        self.user = user
        model = S3FilesTreeModel(user=self.user)
        self.setModel(model)
        self.setup_header()
        self.doubleClicked.connect(self.item_double_clicked)
        self.collapsed.connect(self.model().view_collapsed)
        self.expanded.connect(self.model().view_expanded)

    @property
    def type(self):
        return 's3'

    def refresh(self):
        self.collapsed.disconnect()
        self.expanded.disconnect()
        model = S3FilesTreeModel(user=self.user)
        prev_model = self.model()
        prev_selection_model = self.selectionModel()
        self.setModel(model)
        self.collapsed.connect(self.model().view_collapsed)
        self.expanded.connect(self.model().view_expanded)
        if self.location_bar.text() != self.root:
            self.location_bar.clear()
            self.location_bar.insert(self.root)
        if prev_model:
            prev_model.deleteLater()
        if prev_selection_model:
            prev_selection_model.deleteLater()


class DigitalOceanFileListingView(BaseS3FileListingView):

    def __init__(self, user, parent=None):
        super().__init__(parent)
        user = user.copy()
        if not user['Root'].startswith('/'):
            user['Root'] = '/' + user['Root']
        self.root = user['Root']
        self.user = user
        self.location_bar = None
        self.info_bar = None
        model = DigitalOceanFilesTreeModel(user=self.user)
        self.setModel(model)
        self.setup_header()
        self.doubleClicked.connect(self.item_double_clicked)
        self.collapsed.connect(self.model().view_collapsed)
        self.expanded.connect(self.model().view_expanded)

    @property
    def type(self):
        return 'digital ocean'

    def refresh(self):
        self.collapsed.disconnect()
        self.expanded.disconnect()
        model = DigitalOceanFilesTreeModel(user=self.user)
        prev_model = self.model()
        prev_selection_model = self.selectionModel()
        self.setModel(model)
        self.collapsed.connect(self.model().view_collapsed)
        self.expanded.connect(self.model().view_expanded)
        if self.location_bar.text() != self.root:
            self.location_bar.clear()
            self.location_bar.insert(self.root)
        if prev_model:
            prev_model.deleteLater()
        if prev_selection_model:
            prev_selection_model.deleteLater()
