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
    QItemSelectionModel,
    QModelIndex,
    QThreadPool,
    Signal,
    Slot,
)
from PySide6.QtGui import (
    QIcon,
    QDrag,
    QDragMoveEvent,
    QDropEvent,
)
from PySide6.QtWidgets import (
    QAbstractItemView,
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
        acceptable_schemes = {'file', 's3'}
        if urls := event.mimeData().urls():
            if all(i.scheme().lower() in acceptable_schemes for i in urls):
                self.selectionModel().clearSelection()
                dest_index = self.indexAt(event.pos())
                if dest_index.isValid():
                    if dest_index.model().hasChildren(dest_index):
                        self.selectionModel().select(
                            dest_index,
                            QItemSelectionModel.Select
                        )
                    elif (parent := dest_index.parent()).isValid():
                        self.selectionModel().select(
                            parent,
                            QItemSelectionModel.Select
                        )
                event.accept()
                return
        event.ignore()

    @Slot(QDropEvent)
    def dropEvent(self, event):
        # event.source() == originator
        # self == destination
        if urls := event.mimeData().urls():
            if self is event.source():
                print('Not implemented yet')
                event.ignore()
                return
            dest_index = self.indexAt(event.pos())
            if dest_index.isValid():
                if dest_index.model().hasChildren(dest_index):
                    dest_path = dest_index.model().filePath(dest_index)
                else:
                    dest_path = dest_index.model().filePath(
                        dest_index.parent()
                    )
            else:
                dest_path = self.root
            destination = items.account_to_item(
                items.new_client(self.client, dest_path), is_dir=True
            )
            files = []
            folders = []
            if event.source() is None:
                # From outside the App; assumes it's a local fileystem for now
                parent = self
                source_type = items.LocalItem
                base_client = settings.new_client(
                    act_type='Local',
                    root=os.path.dirname(urls[0].path())
                )
                for url in urls:
                    client = base_client.copy()
                    client['Root'] = url.path()
                    if os.path.isdir(url.path()):
                        folders.append(source_type(client, is_dir=True))
                    else:
                        file_info = os.stat(url.path())
                        files.append(
                            source_type(
                                client,
                                size=file_info.st_size,
                                mtime=file_info.st_mtime,
                                ctime=file_info.st_ctime
                            )
                        )
            else:
                parent = event.source()
                model = event.source().model()
                source_type = items.types[event.source().type.lower()]
                for i in event.source().selectedIndexes():
                    if i.column() == 0:
                        if item := model.item_from_index(i):
                            if item.is_dir:
                                folders.append(item)
                            else:
                                files.append(item)
            if files and folders:
                action = actions.listings.QueueRecursiveItemsAction(
                    parent, files, folders, destination
                )
            elif files:
                action = actions.listings.QueueFilesAction(
                    parent, files, destination
                )
            elif folders:
                action = actions.listings.QueueFoldersAction(
                    parent, folders, destination
                )
            else:
                logging.warn(
                    f'Failed a dropEvent from {event.source()} to {self}'
                )
                event.ignore()
                return
            runnable = action.runnable()
            runnable.signals.aborted.connect(partial(print, 'Aborted!'))
            runnable.signals.update.connect(print)
            # runnable.signals.process_queue.connect(self.start_queue_tmp)
            runnable.signals.select.connect(
                self.parent().parent().parent().parent(
                    ).transfers_window.tabs.widget(0).model().delta_select
            )
            runnable.signals.ss_callback.connect(utils.execute_ss_callback)
            runnable.signals.callback.connect(utils.execute_callback)
            runnable.signals.finished.connect(print)
            runnable.signals.finsihed.connect(
                self.parent().parent().parent().parent(
                    ).transfers_window.tabs.widget(0).model().delta_select
            )
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

    def __init__(self, client, parent=None):
        super().__init__(parent)
        client = client.copy()
        if root := client.get('Root'):
            self.root = root
        else:
            self.root = os.path.expanduser('~')
        self.client = client
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
    def clone(cls, client, parent):
        return cls(client, parent=parent)

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
            self.client['Root'] = location
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
                    _client = self.client.copy()
                    _client['Root'] = item.filePath()
                    if item.isFile():
                        standard_item = LocalItem(
                            _client, size=item.size()
                        )
                        files.append(standard_item)
                    else:
                        standard_item = LocalItem(
                            _client, is_dir=True
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
        self.client = None
        self.root = None

    @classmethod
    def clone(cls, client, parent):
        return cls(client, parent=parent)

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
            self.client['Root'] = location
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

    def __init__(self, client, parent=None):
        super().__init__(parent)
        client = client.copy()
        if not client['Root'].startswith('/'):
            client['Root'] = '/' + client['Root']
        self.root = client['Root']
        self.client = client
        model = S3FilesTreeModel(client=self.client)
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
        model = S3FilesTreeModel(client=self.client)
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

    def __init__(self, client, parent=None):
        super().__init__(parent)
        client = client.copy()
        if not client['Root'].startswith('/'):
            client['Root'] = '/' + client['Root']
        self.root = client['Root']
        self.client = client
        self.location_bar = None
        self.info_bar = None
        model = DigitalOceanFilesTreeModel(client=self.client)
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
        model = DigitalOceanFilesTreeModel(client=self.client)
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
