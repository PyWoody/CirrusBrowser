import logging
import threading
import os

from cirrus import utils
from cirrus.items import DigitalOceanItem, S3Item
from cirrus.statuses import TransferPriority

from PySide6.QtCore import (
    QAbstractListModel,
    QAbstractTableModel,
    QModelIndex,
    Qt,
    Signal,
    Slot,
)
from PySide6.QtGui import QStandardItemModel, QStandardItem
from PySide6.QtSql import QSqlTableModel
from PySide6.QtWidgets import QFileSystemModel


class TransfersTableModel(QSqlTableModel):

    def __init__(self, *, db, parent=None):
        super().__init__(db=db, parent=parent)
        self.last_invalidate = utils.date.epoch()
        self.num_custom_cols = 2
        self.progress_bar_col = 3
        self.progress_rate_col = 4
        self.db_size_col = 5
        self.db_priority_col = 6
        self.db_status_col = 7
        self.align_left_cols = {1, 2}
        # TODO: connect to any row add slots to reset this
        self.transfer_items = dict()
        self.total_rows = 0

    def select(self, *args, **kwargs):
        self.last_invalidate = utils.date.now()
        return super().select()

    def delta_select(self, *, delta=2):
        if (utils.date.now() - self.last_invalidate).seconds >= delta:
            return self.select()

    def columnCount(self, parent=QModelIndex()):
        return super().columnCount() + self.num_custom_cols

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return
        column = index.column()
        if column > self.num_custom_cols:
            index = self.createIndex(
                index.row(), column - self.num_custom_cols
            )
        if role == Qt.DisplayRole:
            pk = super().data(index.siblingAtColumn(0), role)
            if column == 0:
                return pk
            elif column == self.progress_bar_col:
                if item := self.transfer_items.get(pk):
                    return item.progress
                return 0
            elif column == self.progress_rate_col:
                if item := self.transfer_items.get(pk):
                    return item.rate
                return
            elif column == self.db_size_col:
                if size := super().data(index, role):
                    return f'{size:,}'
                elif pk:
                    return 0
                return
            elif column == self.db_priority_col:
                if priority := super().data(index, role):
                    name = TransferPriority(priority).name
                    return ' '.join(
                        [i.capitalize() for i in name.split('_')]
                    )
                return 'Normal'
        elif role == Qt.TextAlignmentRole:
            if column in self.align_left_cols:
                return Qt.AlignLeft
            elif column == self.db_priority_col:
                return Qt.AlignCenter
            return Qt.AlignRight
        return super().data(index, role)

    def canFetchMore(self, parent=QModelIndex()):
        if parent.isValid():
            return False
        can = super().canFetchMore(parent)
        if not can:
            # TODO: Check this. Smaller numbers cause infinite recursion
            if self.rowCount(parent) > 100:
                self.select()
                can = super().canFetchMore(parent)
        return can

    def fetchMore(self, parent=QModelIndex()):
        if parent.isValid():
            return
        current_rows = self.rowCount(parent)
        super().fetchMore(parent)
        self.beginInsertRows(parent, current_rows, self.rowCount(parent) - 1)
        self.endInsertRows()

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        """
            [ H ] Pk
            Progress
            Rate
            Status
            Source
            Destination
            Size
            Priority
            [ H ] Status
            [ H ] Start Time
            [ H ] End Time
            [ H ] Error Mesage
        """
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            if section == self.progress_bar_col:
                return 'Progress'
            elif section == self.progress_rate_col:
                return 'Rate'
            if section > self.num_custom_cols:
                section -= self.num_custom_cols
            if data := super().headerData(section, orientation, role):
                data = str(data).strip().replace('_', ' ')
                return ' '.join([i.capitalize() for i in data.split(' ')])
        return super().headerData(section, orientation, role)

    @Slot(QModelIndex)
    def flags(self, index):
        if index.isValid():
            return Qt.ItemIsSelectable | Qt.ItemIsEnabled
        return Qt.NoItemFlags


class FinishedTableModel(QSqlTableModel):

    def __init__(self, *, db, parent=None):
        super().__init__(db=db, parent=parent)
        self.last_invalidate = utils.date.epoch()

    def select(self, *args, **kwargs):
        self.last_invalidate = utils.date.now()
        return super().select()

    def delta_select(self, *, delta=2):
        if (utils.date.now() - self.last_invalidate).seconds >= delta:
            return self.select()

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or role != Qt.DisplayRole:
            return
        return super().data(index, role)

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            if data := super().headerData(section, orientation, role):
                data = data.strip().replace('_', ' ')
                return ' '.join([i.capitalize() for i in data.split(' ')])

    def flags(self, index):
        if index.isValid():
            return Qt.ItemIsSelectable | Qt.ItemIsEnabled
        return Qt.NoItemFlags


class LocalFileSystemModel(QFileSystemModel):

    def __init__(self, parent=None):
        super().__init__(parent)

    @Slot(list)
    def remove_rows(self, items):
        for item in items:
            text = os.path.basename(item.root.strip('/').strip('\\'))
            for result in self.findItems(
                text, Qt.MatchRecursive | Qt.MatchExactly | Qt.MatchWrap, 0
            ):
                if data := result.data():
                    if data.root == item.root:
                        index = self.indexFromItem(result)
                        result_parent = index.parent()
                        self.removeRow(index.row(), result_parent)


class BaseS3FilesTreeModel(QStandardItemModel):
    new_folder_item = Signal(object, str, dict)
    new_file_item = Signal(object, tuple, dict)
    all_items_loaded = Signal(object)
    no_children = Signal(object)
    loading_row = Signal(QStandardItem)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._stopped = False

    def hasChildren(self, parent=QModelIndex()):
        if not parent.isValid():
            return True
        if item := self.itemFromIndex(parent):
            if data := item.data():
                if data.is_dir:
                    return True
        return False

    def canFetchMore(self, parent=QModelIndex()):
        if parent.isValid():
            return False
        return self.valid_last_row

    def fetchMore(self, parent=QModelIndex()):
        if parent.isValid():
            return
        new_current_row = self.current_row + self.max_keys
        self.beginInsertRows(parent, self.current_row, new_current_row)
        self.current_row = new_current_row
        self.endInsertRows()
        if not self.data(self.index(self.current_row, 0)):
            last_row = self.current_row - 1
            while last_row > 0:
                if self.data(self.index(last_row, 0)):
                    break
                last_row -= 1
            self.current_row = last_row + 1
            self.valid_last_row = False

    def fetch_children(self, item, parent=None):
        parent = self.invisibleRootItem() if parent is None else parent
        self.loading_row.emit(parent)
        t = threading.Thread(
            args=(item, parent),
            target=self.__fetch_children,
            daemon=True
        )
        t.start()

    def __fetch_children(self, item, parent):
        client = item.setup_client()
        client_config = item.config.copy()
        found = False
        logging.info(f'Starting fetch for {client_config} | {parent}')
        response = client.list_objects_v2(**client_config)
        for content in response.get('CommonPrefixes', []):
            if self._stopped:
                return
            fname = content['Prefix'].strip('/').split('/')[-1]
            root = f'{client_config["Bucket"]}/{content["Prefix"]}'
            item_data = {'root': root, 'is_dir': True}
            # TODO: This causes a runtime error if parent is deleted
            #       before we get to this point
            #       Should do a is_alive style check and return otherwise
            # TODO: Just make it a helper func so it can be shared everywhere
            #       parent == QStandardItem
            if parent_data := parent.data():
                if parent_data.collapsed:
                    logging.info(f'{parent} exited due to collapse.')
                    return
            self.new_folder_item.emit(parent, fname, item_data)
            if not found:
                found = True
        for content in response.get('Contents', []):
            if self._stopped:
                return
            if (key := content['Key']) != client_config['Prefix']:
                fname = key.split('/')[-1]
                file_path = f'/{client_config["Bucket"]}/{key}'
                item_data = {
                    'root': file_path,
                    'size': content['Size'],
                    'is_dir': False,
                    'mtime': content.get('LastModified', 0),
                }
                if parent_data := parent.data():
                    if parent_data.collapsed:
                        logging.info(f'{parent} exited due to collapse.')
                        return
                self.new_file_item.emit(
                    parent,
                    (
                        fname,
                        f'{content["Size"]:,}',
                        utils.date.to_iso(content['LastModified']),
                    ),
                    item_data
                )
                if not found:
                    found = True
        while response.get('IsTruncated'):
            if self._stopped:
                return
            client_config['ContinuationToken'] = response['NextContinuationToken']
            response = client.list_objects_v2(**client_config)
            for content in response.get('CommonPrefixes', []):
                if self._stopped:
                    return
                fname = content['Prefix'].strip('/').split('/')[-1]
                root = f'{client_config["Bucket"]}/{content["Prefix"]}'
                item_data = {
                    'root': root,
                    'bucket': client_config['Bucket'],
                    'space': content['Prefix'],
                    'is_dir': True,
                    'mtime': content.get('LastModified', 0),
                }
                if parent_data := parent.data():
                    if parent_data.collapsed:
                        logging.info(f'{parent} exited due to collapse.')
                        return
                self.new_folder_item.emit(parent, fname, item_data)
                if not found:
                    found = True
            for content in response.get('Contents', []):
                if self._stopped:
                    return
                if (key := content['Key']) != client_config['Prefix']:
                    fname = key.split('/')[-1]
                    file_path = f'/{client_config["Bucket"]}/{key}'
                    item_data = {
                        'root': file_path,
                        'size': content['Size'],
                        'is_dir': False,
                        'mtime': content.get('LastModified', 0),
                    }
                    if parent_data := parent.data():
                        if parent_data.collapsed:
                            logging.info(f'{parent} exited due to collapse.')
                            return
                    self.new_file_item.emit(
                        parent,
                        (
                            fname,
                            f'{content["Size"]:,}',
                            utils.date.to_iso(content['LastModified']),
                        ),
                        item_data
                    )
                    if not found:
                        found = True
        if not found:
            # Will segfault without assigning index() to a value
            self.no_children.emit(parent)
        else:
            self.all_items_loaded.emit(parent)
        logging.info(f'End fetch for {client_config} | {parent}')

    @Slot(QStandardItem)
    def create_loading_row(self, parent):
        if not self._stopped:
            item = QStandardItem('Fetching...')
            parent.appendRow(item)

    @Slot(QStandardItem)
    def remove_loading_row(self, parent):
        if not self._stopped:
            parent.removeRow(parent.rowCount() - 1)

    @Slot(QStandardItem)
    def no_items_found(self, parent):
        if not self._stopped:
            parent.removeRow(parent.rowCount() - 1)
            parent.appendRow(QStandardItem('(Empty)'))

    @Slot(QModelIndex)
    def view_collapsed(self, index):
        """Removes all rows starting from `index`. The rows cannot be
        gauranteed to exist on the next expand, so they need to be removed
        from the tree.
        """
        item = self.itemFromIndex(index)
        data = item.data()
        if data.is_dir:
            data.collapsed = True
            item.setData(data)
            item.removeRows(0, item.rowCount())

    @Slot(QModelIndex)
    def view_expanded(self, index):
        if item := self.itemFromIndex(index):
            if data := item.data():
                if data.is_dir:
                    if data.collapsed:
                        data.collapsed = False
                        item.setData(data)
                    self.fetch_children(data, item)
                    return
        logging.warn(f'No item/data for {index} in view_expanded')

    @Slot(list)
    def remove_rows(self, items):
        for item in items:
            text = os.path.basename(item.root.strip('/').strip('\\'))
            for result in self.findItems(
                text, Qt.MatchRecursive | Qt.MatchExactly | Qt.MatchWrap, 0
            ):
                if data := result.data():
                    if data.root == item.root:
                        index = self.indexFromItem(result)
                        result_parent = index.parent()
                        self.removeRow(index.row(), result_parent)


class S3FilesTreeModel(BaseS3FilesTreeModel):

    def __init__(self, *, user, parent=None, max_keys=1_000):
        super().__init__(parent)
        self.user = user.copy()
        self.new_folder_item.connect(self.create_folder_item)
        self.new_file_item.connect(self.create_file_item)
        self.all_items_loaded.connect(self.remove_loading_row)
        self.no_children.connect(self.no_items_found)
        self.loading_row.connect(self.create_loading_row)
        self.setHorizontalHeaderLabels(['Name', 'Size', 'Last Modified'])
        self.max_keys = max_keys
        self.current_row = 0
        # TODO: connect to any row add slots to reset this
        self.valid_last_row = True
        # TODO: Cancel specific threads
        self.fetch_children(S3Item(self.user, is_dir=True))

    @Slot(QStandardItem, str, dict)
    def create_folder_item(self, parent, fname, data):
        if not self._stopped:
            if parent_data := parent.data():
                if parent_data.collapsed:
                    logging.info(f'{parent} exited due to collapse.')
                    return
            loading_row = parent.rowCount()
            _user = self.user.copy()
            _user.update(data)
            _user['Root'] = data['root']  # Needs to be smarter
            item_data = S3Item(_user, is_dir=True)
            item = QStandardItem(fname)
            item.setData(item_data)
            parent.insertRow(loading_row - 1, [item])
            self.valid_last_row = True

    @Slot(QStandardItem, tuple, dict)
    def create_file_item(self, parent, items, data):
        if not self._stopped:
            if parent_data := parent.data():
                if parent_data.collapsed:
                    logging.info(f'{parent} exited due to collapse.')
                    return
            loading_row = parent.rowCount()
            out_items = [QStandardItem(item_str) for item_str in items]
            _user = self.user.copy()
            _user.update(data)
            out_items[0].setData(S3Item(_user))
            parent.insertRow(loading_row - 1, out_items)
            self.valid_last_row = True


class DigitalOceanFilesTreeModel(BaseS3FilesTreeModel):

    def __init__(self, *, user, parent=None, max_keys=1_000):
        super().__init__(parent)
        self.user = user.copy()
        self.new_folder_item.connect(self.create_folder_item)
        self.new_file_item.connect(self.create_file_item)
        self.all_items_loaded.connect(self.remove_loading_row)
        self.no_children.connect(self.no_items_found)
        self.loading_row.connect(self.create_loading_row)
        self.setHorizontalHeaderLabels(['Name', 'Size', 'Last Modified'])
        self.max_keys = max_keys
        self.current_row = 0
        # TODO: connect to any row add slots to reset this
        self.valid_last_row = True
        # TODO: Cancel specific threads
        self.fetch_children(DigitalOceanItem(self.user, is_dir=True))

    @Slot(QStandardItem, str, dict)
    def create_folder_item(self, parent, fname, data):
        if not self._stopped:
            if parent_data := parent.data():
                if parent_data.collapsed:
                    logging.info(f'{parent} exited due to collapse.')
                    return
            loading_row = parent.rowCount()
            _user = self.user.copy()
            _user.update(data)
            _user['Root'] = data['root']  # Needs to be smarter
            item_data = DigitalOceanItem(_user, is_dir=True)
            item = QStandardItem(fname)
            item.setData(item_data)
            parent.insertRow(loading_row - 1, [item])
            self.valid_last_row = True

    @Slot(QStandardItem, tuple, dict)
    def create_file_item(self, parent, items, data):
        if not self._stopped:
            if parent_data := parent.data():
                if parent_data.collapsed:
                    logging.info(f'{parent} exited due to collapse.')
                    return
            loading_row = parent.rowCount()
            out_items = [QStandardItem(item_str) for item_str in items]
            _user = self.user.copy()
            _user.update(data)
            out_items[0].setData(DigitalOceanItem(_user))
            parent.insertRow(loading_row - 1, out_items)
            self.valid_last_row = True


class SearchResultsModel(QAbstractTableModel):

    def __init__(self, parent=None, items=None):
        super().__init__(parent)
        self.items = list(items) if items is not None else []
        self.current_row = 0
        self._stopped = False

    def columnCount(self, parent=QModelIndex()): 
        return 4

    def rowCount(self, parent=QModelIndex()):
        if parent.isValid():
            return 0
        return len(self.items)

    def canFetchMore(self, parent=QModelIndex()):
        if parent.isValid():
            return False
        return self.current_row < len(self.items)

    def fetchMore(self, parent=QModelIndex()):
        if parent.isValid():
            return
        items_to_fetch = min(100, len(self.items) - self.current_row)
        if items_to_fetch <= 0:
            return
        self.beginInsertRows(
            parent,
            self.current_row,
            self.current_row + items_to_fetch - 1
        )
        self.current_row += items_to_fetch
        self.endInsertRows()

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return
        if role == Qt.DisplayRole:
            return self.items[index.row()][index.column()]
        if role == Qt.CheckStateRole and index.column() == 0:
            status = self.items[index.row()][index.column()]
            if status == Qt.Checked:
                return Qt.Checked
            return Qt.Unchecked

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            if section == 0:
                return ''
            elif section == 1:
                return 'Name'
            elif section == 2:
                return 'Size'
            elif section == 3:
                return 'Last Modified'

    @Slot(QModelIndex)
    def flags(self, index):
        if index.isValid():
            if index.column() == 0:
                return Qt.ItemNeverHasChildren | \
                       Qt.ItemIsEnabled | \
                       Qt.ItemIsUserCheckable | \
                       Qt.ItemIsSelectable
            return Qt.ItemIsEnabled | \
                   Qt.ItemNeverHasChildren | \
                   Qt.ItemIsSelectable
        return Qt.NoItemFlags

    def insertRows(self, row, count, parent=QModelIndex()):
        try:
            self.beginInsertRows(parent, row, count)
            self.endInsertRows()
        except Exception as e:
            cls_name = self.__class__.__name__
            logging.warn(
                (f'Could not add {count} new '
                 f'rows starting from {row} to {cls_name}: {e:!r}')
            )
            return False
        else:
            return True

    def setData(self, index, value, role=Qt.EditRole):
        try:
            if index.column() == 0 and role == Qt.CheckStateRole:
                if value == Qt.Checked.value or value == Qt.Checked:
                    value = Qt.Checked
                else:
                    value = Qt.Unchecked
            else:
                return False
            self.items[index.row()][index.column()] = value
        except Exception as e:
            cls_name = self.__class__.__name__
            logging.warn(f'Could not setData {value} on {index}: {e:!r}')
            return False
        else:
            self.dataChanged.emit(index, index)
            return True

    def completed(self):
        if not self.rowCount():
            # TODO: This is broken I think
            self.items = [['', 'No items found']]
            self.insertRows(0, 1)

    @Slot(list)
    def add_results(self, items):
        for item in items:
            self.items.append(
                [
                    Qt.Unchecked,
                    item.root,
                    item.size,
                    utils.date.to_iso(item.mtime) if item.mtime else ''
                ]
            )
        return self.insertRows(self.rowCount(), len(items))

    @Slot(object)
    def add_result(self, item):
        self.items.append(
            [
                Qt.Unchecked,
                item.root,
                item.size,
                utils.date.to_iso(item.mtime) if item.mtime else ''
            ]
        )
        return self.insertRows(self.rowCount(), 1)


class ListModel(QAbstractListModel):

    def __init__(self, items=None):
        super().__init__()
        self.items = list(items) if items is not None else []

    def rowCount(self, parent=QModelIndex()):
        return len(self.items)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return
        if role == Qt.DisplayRole:
            return self.items[index.row()]

    def update_items(self, items):
        if items:
            self.beginResetModel()
            self.items = list(items)
            self.endResetModel()
