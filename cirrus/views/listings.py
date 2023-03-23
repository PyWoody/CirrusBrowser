import os

from cirrus import utils
from cirrus.items import LocalItem
from cirrus.models import (
    DigitalOceanFilesTreeModel,
    LocalFileSystemModel,
    S3FilesTreeModel
)
from cirrus.validators import LocalPathValidator

from PySide6.QtCore import (
    QDir,
    Qt,
    QModelIndex,
    QItemSelection,
    Signal,
    Slot,
)
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QTreeView,
)


class FileListingTreeView(QTreeView):
    status_bar_change = Signal(str)
    location_bar_change = Signal(str)
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

    def refresh(self):
        raise NotImplementedError('Must specificy refrresh() in a subclass')


class LocalFileListing(FileListingTreeView):
    # TODO: Turn off auto updating. It's very slow

    def __init__(self, user, parent=None):
        super().__init__(parent)
        if root := user.get('Root'):
            self.root = root
        else:
            self.root = os.path.expanduser('~')
        self.user = user
        self.location_bar = None
        self.status_bar = None
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

    def create_location_bar(self, window_type='Local'):
        self.location_bar = QLineEdit()
        self.location_bar.setValidator(LocalPathValidator())
        self.location_bar.insert(self.root)
        self.location_bar.editingFinished.connect(self.change_dir)
        self.location_bar_change.connect(self.update_location_bar)
        window_type_label = QLabel(window_type)
        window_location_bar_layout = QHBoxLayout()
        window_location_bar_layout.addWidget(window_type_label)
        window_location_bar_layout.addWidget(self.location_bar)
        return window_location_bar_layout

    def create_status_bar(self):
        self.status_bar = None
        self.status_bar = QLabel()
        self.status_bar_change.connect(self.update_status_bar)
        return self.status_bar

    @classmethod
    def clone(cls, user, parent):
        return cls(user, parent=parent)

    def refresh(self):
        model = LocalFileSystemModel()
        model.setFilter(
            QDir.AllEntries | QDir.NoDotAndDotDot | QDir.AllDirs | QDir.Hidden
        )
        model.setRootPath(self.root)
        self.setModel(model)
        self.setRootIndex(model.index(self.root))

    @Slot()
    def change_dir(self):
        # TODO: Need to re-evaluate if tracking self.root outside of
        #       self.user is still necessary
        self.root = self.location_bar.text()
        self.user['Root'] = self.root
        self.root_changed.emit(self.root)
        self.refresh()

    @Slot(str)
    def update_location_bar(self, path):
        if os.path.isdir(path):
            self.root = path
            self.location_bar.clear()
            self.location_bar.insert(self.root)
            self.change_dir()

    @Slot(str)
    def update_status_bar(self, status):
        self.status_bar.setText(status)

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
        self.status_bar_change.emit(output)
        super().selectionChanged(selected, deselected)


class BaseS3FileListing:

    def create_location_bar(self, window_type='S3'):
        self.location_bar = QLineEdit()
        # TODO: The validator will wait until S3 is normalized
        # self.location_bar.setValidator(S3PathValidator())
        self.location_bar.insert(self.root)
        self.location_bar.editingFinished.connect(self.change_dir)
        self.location_bar_change.connect(self.update_location_bar)
        window_type_label = QLabel(window_type)
        window_location_bar_layout = QHBoxLayout()
        window_location_bar_layout.addWidget(window_type_label)
        window_location_bar_layout.addWidget(self.location_bar)
        return window_location_bar_layout

    def create_status_bar(self):
        self.status_bar = None
        self.status_bar = QLabel()
        self.status_bar_change.connect(self.update_status_bar)
        return self.status_bar

    @classmethod
    def clone(cls, root, parent):
        return cls(root=root, parent=parent)

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
        self.status_bar_change.emit(output)
        super().selectionChanged(selected, deselected)

    @Slot()
    def change_dir(self):
        # TODO: This is slow in the view. Use the main status_bar
        #       to inform the user the move has started
        self.root = self.location_bar.text()
        self.user['Root'] = self.root
        self.root_changed.emit(self.root)
        self.refresh()

    @Slot(str)
    def update_location_bar(self, root):
        self.location_bar.clear()
        self.location_bar.insert(root)
        self.change_dir()

    @Slot(str)
    def update_status_bar(self, status):
        self.status_bar.setText(status)


class S3FileListing(BaseS3FileListing, FileListingTreeView):

    def __init__(self, user, parent=None):
        super().__init__(parent)
        user = user.copy()
        if not user['Root'].startswith('/'):
            user['Root'] = '/' + user['Root']
        self.root = user['Root']
        self.user = user
        self.location_bar = None
        self.status_bar = None
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
        self.setModel(model)
        self.collapsed.connect(self.model().view_collapsed)
        self.expanded.connect(self.model().view_expanded)


class DigitalOceanFileListing(BaseS3FileListing, FileListingTreeView):

    def __init__(self, user, parent=None):
        super().__init__(parent)
        user = user.copy()
        if not user['Root'].startswith('/'):
            user['Root'] = '/' + user['Root']
        self.root = user['Root']
        self.user = user
        self.location_bar = None
        self.status_bar = None
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
        self.setModel(model)
        self.collapsed.connect(self.model().view_collapsed)
        self.expanded.connect(self.model().view_expanded)
