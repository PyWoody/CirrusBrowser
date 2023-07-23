import collections
import gc
import logging
import os
import queue
import sqlite3
import threading

from functools import wraps

from cirrus import exceptions, items, settings, utils
from cirrus.statuses import TransferPriority, TransferStatus

from PySide6.QtSql import QSqlDatabase,  QSqlQuery
from PySide6.QtCore import (
    QMutex,
    QObject,
    Signal,
    Slot,
)
from PySide6.QtWidgets import QWidget

# TODO: This was mean to be tmp. Requires total rewrite
#       Need to re-write using signals/slots for correct updating in main db
#       Models can't track updates via threads and become stale
# TODO: transfer_priroity_change
# NOTE: `add` should really be `insert`

# TODO: Have Database initiate a thread for an iterable queue
#       of func, args, db_name=the_thread_db_name

_global_mutex = QMutex()


def db_logger(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        logging.debug(
            f'Database: {func.__name__}(args:{args!r}, kwargs:{kwargs!r}'
        )
        result = func(*args, **kwargs)
        logging.debug(
            f'Database: {func.__name__}(args:{args!r}, '
            f'kwargs:{kwargs!r} -> {result}'
        )
        return result
    return wrapper


class IterableQueue(queue.Queue):
    SENTINEL = object()

    def __iter__(self):
        while True:
            try:
                item = self.get()
                if item is self.SENTINEL:
                    return
                yield item
            finally:
                self.task_done()

    def close(self):
        self.put(self.SENTINEL)


class Database(QWidget):
    new_task = Signal(object, list)
    success = Signal(list)
    failure = Signal(list)

    def __init__(self,  parent=None):
        super().__init__(parent)
        self.lock = threading.Lock()
        self.queue = IterableQueue()
        self.db_con_name = 'con_db_process'
        self.started = False
        self.new_task.connect(self.__add_task_from_thread)

    def start(self):
        with self.lock:
            if not self.started:
                t = threading.Thread(target=self.__process, daemon=True)
                t.start()
                self.started = True

    def add_recursive_task(self, func, sources, destination):
        t = threading.Thread(
            target=self.__walk,
            args=(func, sources, destination),
            daemon=True
        )
        t.start()

    def __walk(self, func, sources, destination):
        # NOTE: This will be an Item func that handles itself
        num_files = 0
        output_groups = []
        for source in sources:
            for root, dirs, files in os.walk(source):
                out_path = os.path.abspath(
                    os.path.join(
                        # This will need to be when ready
                        # destination, os.path.relpath(root, start=source)
                        root
                    )
                )
                out_items = []
                for f in files:
                    num_files += 1
                    # This is an absurd setting but it's clear the select
                    # that is slowing everything down
                    if num_files % 100 == 0:
                        output_groups.append((out_items, out_path))
                        emittable_output = output_groups.copy()
                        self.new_task.emit(func, emittable_output)
                        output_groups = []
                        out_items = []
                    out_fname = os.path.join(out_path, f)
                    client = settings.setup_client(
                        act_type='Local', root=out_fname
                    )
                    out_item = items.LocalItem(client)
                    out_items.append(out_item)
                if out_items:
                    output_groups.append((out_items, out_path))
        if output_groups:
            self.new_task.emit(func, output_groups)

    @Slot(object, list)
    def __add_task_from_thread(self, func, args):
        self.add_task(target=func, transfer_items=(args,))

    # TODO: Normalize these to only be one or the other
    @Slot(object, list)
    @Slot(object, tuple)
    def add_task(self, *, target, transfer_items):
        self.queue.put((target, transfer_items))

    def __process(self):
        with self.lock:
            if self.db_con_name in QSqlDatabase.connectionNames():
                QSqlDatabase.removeDatabase(self.db_con_name)
            con = QSqlDatabase.addDatabase('QSQLITE', self.db_con_name)
            con.setDatabaseName(settings.DATABASE)
            if not con.open():
                raise exceptions.DatabaseClosedException
        for item in self.queue:
            if item is None:
                self.started = False
                return
            func, transfer_items = item
            # TODO: Create this instance at the very top-level in the windows
            #       so it can be closed and joined
            # TODO: Emit `started` and `finished` items
            #       to be dataChanged'd selectRow'd
            try:
                # TODO: Just emit the transfer_items. Let the connected funcs
                #       handle what to do with them.
                #       Don't make this too complicated here
                if func(*transfer_items, con_name=self.db_con_name):
                    self.success.emit(*transfer_items)
                else:
                    self.failure.emit(*transfer_items)
            except RuntimeError as e:
                logging.warn(f'RuntimeError in __process: {str(e)}')


class DatabaseWorkers:

    def __init__(self):
        self.peak_bitrate = 0
        self.total_processed = 0
        self.avg_bitrate = 0
        self.current_bitrate = 0
        self.num_finished_workers = 0
        self.num_current_workers = 0
        self.completed = set()
        self.output = collections.namedtuple(
            'output',
            [
                'num_finished_workers',
                'num_current_workers',
                'peak_bitrate',
                'avg_bitrate',
                'current_bitrate'
            ]
        )

    def __call__(self):
        print(
            f'Updating workers | PREV: {self.num_current_workers}',
            end=''
        )
        self.update()
        print(f' | NOW: {self.num_current_workers}', flush=True)
        output = self.output(
            num_finished_workers=self.num_finished_workers,
            num_current_workers=self.num_current_workers,
            peak_bitrate=self.peak_bitrate,
            avg_bitrate=self.avg_bitrate,
            current_bitrate=self.current_bitrate,
        )
        return output

    def update(self):
        # TODO: Check if local/S3/etc. Will be done in the TransferItem
        worker_found = False
        transferring = set()
        self.num_current_workers = 0
        processed = 0
        done_statuses = {TransferStatus.ERROR, TransferStatus.COMPLETED}
        # No DB will have the epehemeral data.
        # Maybe keep a list in the executor and then pass that to the
        # class from `central.py`
        for item in gc.get_objects():  # I hate me, too
            if isinstance(item, items.TransferItem) and item.pk not in self.completed:  # noqa E501
                if item.status in done_statuses:
                    if not worker_found:
                        worker_found = True
                    self.total_processed += item.processed
                    if (bitrate := item.rate_in_bytes()) > self.peak_bitrate:
                        self.peak_bitrate = bitrate
                    self.num_finished_workers += 1
                    self.completed.add(item.pk)
                elif item.status == TransferStatus.TRANSFERRING:
                    processed += item.processed
                    if item.pk not in transferring:
                        self.num_current_workers += 1
                        transferring.add(item.pk)
        if worker_found:
            self.avg_bitrate = self.total_processed // self.num_finished_workers  # noqa E501
        if self.num_current_workers:
            self.current_bitrate = processed // self.num_current_workers


class DatabaseQueue(QObject):
    # Terrible name. Should convert the __build_queue to an iterable queue
    add_worker = Signal()
    remove_worker = Signal()
    completed = Signal()

    def __init__(self, *, parent=None, max_workers=10):
        super().__init__(parent)
        self.clients = list(settings.saved_clients())
        self.workers = DatabaseWorkers()
        self.max_workers = 10
        self.con_thread_name = 'database_thread'
        self.queue_being_built = False
        self.mutex = QMutex()
        # TODO: Tweak max size wrt timeout
        self.hot_queue = queue.PriorityQueue(maxsize=self.max_workers * 2)
        self.queue_thread = None
        self.__stopped = False

    @Slot()
    def build_queue(self):
        # This smells like shit
        self.mutex.lock()
        if self.queue_being_built:
            self.mutex.unlock()
            return
        self.__stopped = False
        t = threading.Thread(
            target=self.__build_queue,
            name=self.con_thread_name,
            daemon=True,
        )
        self.queue_thread = t
        t.start()
        self.queue_being_built = True
        self.mutex.unlock()

    def __build_queue(self):
        if self.queue_being_built:
            return
        if self.con_thread_name in QSqlDatabase.connectionNames():
            QSqlDatabase.removeDatabase(self.con_thread_name)
        con = QSqlDatabase.cloneDatabase('con', self.con_thread_name)
        if not con.open():
            raise exceptions.DatabaseClosedException
        pk_idx, source_idx, destination_idx, size_idx, priority_idx = range(5)
        source_type_idx, destination_type_idx = 5, 6
        priority = 100  # Default pend to end
        transfer_item = None
        while not self.__stopped:
            try:
                pks_to_update = []
                con.transaction()
                query = QSqlQuery(con)
                query.prepare('''
                    SELECT
                        pk,
                        source,
                        destination,
                        size,
                        priority,
                        source_type,
                        destination_type
                    FROM
                        transfers
                    WHERE
                        status = (?)
                    ORDER BY
                        priority DESC,
                        pk ASC
                    LIMIT
                        (?)
                ''')
                query.addBindValue(TransferStatus.PENDING.value)
                # TODO: Tweak LIMIT wrt to Timeout
                query.addBindValue(self.max_workers * 2)
                if not query.exec():
                    con.rollback()
                    err_msg = query.lastError().databaseText()
                    critical_msg('next_item (exec)', err_msg)
                    # TODO: Error handeling via response
                    self.mutex.lock()
                    self.queue_being_built = False
                    self.mutex.unlock()
                    return
                con.commit()
                while query.next():
                    pk = query.value(pk_idx)
                    size = query.value(size_idx)
                    src = query.value(source_idx)
                    src_act_type = query.value(source_type_idx).lower()
                    # TODO: S3/DO will need the Access Key in the User
                    #       Hmm...
                    #       Maybe build a clients_dict from settings
                    #       check type --> root
                    #       if not found, rebuild dict
                    #       if not found again, raise error
                    src_item_type = items.types[src_act_type]
                    src_client = items.match_client(self.clients, src_act_type, src)
                    if not src_client:
                        self.clients = list(settings.saved_clients())
                        src_client = items.match_client(
                            self.clients, src_act_type, src
                        )
                        if not src_client:
                            # TODO: Add these to the Error tab
                            logging.warn(
                                f'Could not find client for {src}. Skipping'
                            )
                            continue
                    src_client['Root'] = src
                    src_item = src_item_type(src_client, size=size)
                    dst = query.value(destination_idx)
                    dst_act_type = query.value(destination_type_idx).lower()
                    dst_item_type = items.types[dst_act_type]
                    dst_client = items.match_client(self.clients, dst_act_type, dst)
                    if not dst_client:
                        self.clients = list(settings.saved_clients())
                        dst_client = items.match_client(
                            self.clients, dst_act_type, dst
                        )
                        if not dst_client:
                            # TODO: Add these to the Error tab
                            logging.warn(
                                f'Could not find client for {dst}. Skipping'
                            )
                            continue
                    dst_client['Root'] = dst
                    dst_item = dst_item_type(
                        dst_client, size=size
                    )
                    priority = query.value(priority_idx)
                    priority = 3 if priority == 0 else priority
                    transfer_item = items.TransferItem(
                        pk,
                        src_item,
                        dst_item,
                        size,
                        status=TransferStatus.QUEUED,
                        priority=TransferPriority(priority),
                    )
                    pks_to_update.append(pk)
                    try:
                        # TODO: Tweak the timeout and list at start
                        timeout = 2
                        if self.__stopped:
                            timeout = 0
                        self.hot_queue.put(
                            (priority, transfer_item), timeout=timeout
                        )
                    except queue.Full:
                        if not self.__stopped:
                            self.adjust_workers()
                        self.hot_queue.put((priority, transfer_item))
                if not pks_to_update or self.__stopped:
                    self.mutex.lock()
                    self.queue_being_built = False
                    self.mutex.unlock()
                    return
                # Only modifies the cloned db
                con.transaction()
                query = QSqlQuery(con)
                query.prepare('''
                    UPDATE
                        transfers
                    SET
                        status = (?)
                    WHERE
                        pk = (?)
                    ''')
                for pk in pks_to_update:
                    query.addBindValue(TransferStatus.QUEUED.value)
                    query.addBindValue(pk)
                    if not query.exec():
                        con.rollback()
                        err_msg = query.lastError().databaseText()
                        critical_msg('next_item', err_msg)
                        # TODO: Error handeling via response
                        self.mutex.lock()
                        self.queue_being_built = False
                        self.mutex.unlock()
                        return
                con.transaction()
            except Exception as e:
                critical_msg('next_item E', str(e))
                # TODO: Error handeling via response
                self.mutex.lock()
                self.queue_being_built = False
                self.mutex.unlock()
                return
        self.mutex.lock()
        self.queue_being_built = False
        self.mutex.unlock()

    def next_item(self):
        # TODO: When __stopped, clear queue, prioritized Queued Status items
        #       when restarting hotqueue
        while True:
            try:
                # TODO: Tweak timeout
                _, item = self.hot_queue.get(timeout=5)
            except queue.Empty:
                # Timeout emits an Empty Error
                if self.__stopped or not self.queue_being_built:
                    self.completed.emit()
                    return
                self.adjust_workers()
            else:
                self.hot_queue.task_done()
                yield item

    @Slot(str)
    def remove_item(self, item_root):
        '''
        self.mutex.lock()
        tmp_queue = queue.PriorityQueue(maxsize=self.max_workers * 2)
        self.queue_being_built = False
        self.mutex.unlock()
        '''
        pass

    def adjust_workers(self):
        # TODO: Add a remove_worker signal to the executor
        #       subclass when there are too many rate limit hits
        # TODO: Think of a way to smartly calculate
        #       if a thread needs to be killed
        # NOTE: This could potentially be a costly call.
        return
        w = self.workers()
        if not all([w.current_bitrate, w.peak_bitrate, w.avg_bitrate]):
            return
        if w.current_bitrate / w.peak_bitrate >= .5:
            if w.current_bitrate / w.avg_bitrate >= .75:
                self.add_worker.emit()

    def join(self):
        if self.queue_thread:
            # Try to do a cleanup
            print(self.workers())
            self.queue_thread.join(1.0)

    def stop(self):
        self.__stopped = True


@db_logger
def add_transfer(*, item, destination, s_type, d_type, con_name='con'):
    # TODO: Check that item, destination doesn't already exist in the DB
    con = QSqlDatabase.database(con_name)
    if not con.open():
        raise exceptions.DatabaseClosedException
    try:
        con.transaction()
        query = QSqlQuery(con)
        query.prepare('''
            INSERT INTO
                transfers (
                    source, destination, size, source_type, destination_type
                )
            VALUES
                (?, ?, ?, ?, ?)''')
        query.addBindValue(item.root)
        query.addBindValue(destination)
        query.addBindValue(item.size)
        query.addBindValue(s_type)
        query.addBindValue(d_type)
        if not query.exec():
            con.rollback()
            err_msg = query.lastError().databaseText()
            critical_msg('add_transfer', err_msg)
            return False
        con.commit()
        return True
    except Exception as e:
        critical_msg('add_transfer E', str(e))
        con.rollback()
        return False


@db_logger
def drop_rows(*, pks, con_name='con'):
    con = QSqlDatabase.database(con_name)
    if not con.open():
        raise exceptions.DatabaseClosedException
    try:
        con.transaction()
        query = QSqlQuery(con)
        query.prepare('''
            DELETE FROM
                transfers
            WHERE
                pk = (?)''')
        for pk in pks:
            query.addBindValue(pk)
            if not query.exec():
                con.rollback()
                err_msg = query.lastError().driverText()
                # err_msg = query.lastError().databaseText()
                critical_msg('add_transfers', err_msg)
                return False
        con.commit()
        return True
    except Exception as e:
        critical_msg('add_transfers E', str(e))
        con.rollback()
        return False


@db_logger
def add_transfers(*, items, destination, s_type, d_type, con_name='con'):
    # TODO: Check that item, destination doesn't already exist in the DB
    con = QSqlDatabase.database(con_name)
    if not con.open():
        raise exceptions.DatabaseClosedException
    try:
        con.transaction()
        query = QSqlQuery(con)
        query.prepare('''
            INSERT INTO
                transfers (
                    source, destination, size, source_type, destination_type
                )
            VALUES
                (?, ?, ?, ?, ?)''')
        for item in items:
            final_destination = os.path.join(
                destination, os.path.split(item.root)[1]
            )
            query.addBindValue(item.root)
            query.addBindValue(final_destination)
            query.addBindValue(item.size)
            query.addBindValue(s_type)
            query.addBindValue(d_type)
            if not query.exec():
                con.rollback()
                err_msg = query.lastError().driverText()
                # err_msg = query.lastError().databaseText()
                critical_msg('add_transfers', err_msg)
                return False
        if not con.commit():
            con.rollback()
            err_msg = query.lastError().driverText()
            # err_msg = query.lastError().databaseText()
            critical_msg('add_transfers', err_msg)
            return False
        return True
    except Exception as e:
        critical_msg('add_transfers E', str(e))
        con.rollback()
        return False


@db_logger
def add_mixed_destination_items(item_destination_groups, con_name='con'):
    # NOTE: Absolutely god-awful name. MVP
    # This is ally really confusing and not good
    # TODO: Check that item, destination doesn't already exist in the DB
    con = QSqlDatabase.database(con_name)
    if not con.open():
        raise exceptions.DatabaseClosedException
    try:
        con.transaction()
        query = QSqlQuery(con)
        query.prepare('''
            INSERT INTO
                transfers (source, destination, size)
            VALUES
                (?, ?, ?)''')
        for db_items, destination in item_destination_groups:
            for item in db_items:
                query.addBindValue(item.root)
                query.addBindValue(destination)
                query.addBindValue(item.size)
                if not query.exec():
                    con.rollback()
                    # driver_msg = query.lastError().driverText()
                    err_msg = query.lastError().databaseText()
                    critical_msg('add_mixed_destination_items', err_msg)
                    return False
        con.commit()
        return True
    except Exception as e:
        critical_msg('add_mixed_destination_items E', str(e))
        con.rollback()
        return False


@db_logger
def transfer_started(item, con_name='con'):
    # Initiated by main thread
    con = QSqlDatabase.database(con_name)
    if not con.open():
        raise exceptions.DatabaseClosedException
    try:
        con.transaction()
        query = QSqlQuery(con)
        query.prepare('''
            UPDATE
                transfers
            SET
                status = (?), start_time = (?), priority = (?)
            WHERE
                pk = (?)
            ''')
        query.addBindValue(item.status.value)
        query.addBindValue(utils.date.to_iso(item.started))
        query.addBindValue(item.priority.value)
        query.addBindValue(item.pk)
        if not query.exec():
            con.rollback()
            err_msg = query.lastError().databaseText()
            critical_msg('transfer_started', err_msg)
            return False
        con.commit()
        return True
    except Exception as e:
        critical_msg('transfer_started E', str(e))
        con.rollback()
        return False


@db_logger
def transfer_error(item, con_name='con'):
    # Initiated by main thread
    con = QSqlDatabase.database(con_name)
    if not con.open():
        raise exceptions.DatabaseClosedException
    try:
        con.transaction()
        query = QSqlQuery(con)
        query.prepare('''
            UPDATE
                transfers
            SET
                status = (?), error_message = (?), end_time = (?)
            WHERE
                pk = (?)
            ''')
        query.addBindValue(item.status.value)
        query.addBindValue(item.message)
        query.addBindValue(utils.date.to_iso(item.completed))
        query.addBindValue(item.pk)
        if not query.exec():
            con.rollback()
            err_msg = query.lastError().databaseText()
            critical_msg('transfer_error', err_msg)
            return False
        con.commit()
        return True
    except Exception as e:
        critical_msg('transfer_error E', str(e))
        con.rollback()
        return False


@db_logger
def transfer_completed(item, con_name='con'):
    # Initiated by main thread
    con = QSqlDatabase.database(con_name)
    if not con.open():
        raise exceptions.DatabaseClosedException
    try:
        con.transaction()
        query = QSqlQuery(con)
        query.prepare('''
            UPDATE
                transfers
            SET
                status = (?), end_time = (?)
            WHERE
                pk = (?)
            ''')
        query.addBindValue(item.status.value)
        query.addBindValue(utils.date.to_iso(item.completed))
        query.addBindValue(item.pk)
        if not query.exec():
            con.rollback()
            err_msg = query.lastError().databaseText()
            critical_msg('transfer_completed', err_msg)
            return False
        con.commit()
        return True
    except Exception as e:
        critical_msg('transfer_completed E', str(e))
        con.rollback()
        return False


@db_logger
def queued_batch_update(pks_to_update, con_name='con'):
    con = QSqlDatabase.database(con_name)
    if not con.open():
        raise exceptions.DatabaseClosedException
    try:
        con.transaction()
        query = QSqlQuery(con)
        query.prepare('''
            UPDATE
                transfers
            SET
                status = (?)
            WHERE
                pk = (?)
            ''')
        for pk in pks_to_update:
            query.addBindValue(TransferStatus.QUEUED.value)
            query.addBindValue(pk)
            if not query.exec():
                con.rollback()
                err_msg = query.lastError().databaseText()
                critical_msg('queued_batch_update', err_msg)
                return False
        con.commit()
        return True
    except Exception as e:
        critical_msg('queued_batch_update E', str(e))
        con.rollback()
        return False


@db_logger
def started_batch_update(transfer_items, con_name='con'):
    # Initiated by main thread
    con = QSqlDatabase.database(con_name)
    if not con.open():
        raise exceptions.DatabaseClosedException
    try:
        con.transaction()
        query = QSqlQuery(con)
        query.prepare('''
            UPDATE
                transfers
            SET
                status = (?), start_time = (?), priority = (?)
            WHERE
                pk = (?)
            ''')
        for item in transfer_items:
            query.addBindValue(item.status.value)
            query.addBindValue(utils.date.to_iso(item.started))
            query.addBindValue(item.priority.value)
            query.addBindValue(item.pk)
            if not query.exec():
                con.rollback()
                err_msg = query.lastError().databaseText()
                critical_msg('transfer_started', err_msg)
                return False
        con.commit()
        return True
    except Exception as e:
        critical_msg('transfer_started E', str(e))
        con.rollback()
        return False


@db_logger
def error_batch_update(transfer_items, con_name='con'):
    # Initiated by main thread
    con = QSqlDatabase.database(con_name)
    if not con.open():
        raise exceptions.DatabaseClosedException
    try:
        con.transaction()
        query = QSqlQuery(con)
        query.prepare('''
            UPDATE
                transfers
            SET
                status = (?), error_message = (?), end_time = (?)
            WHERE
                pk = (?)
            ''')
        for item in transfer_items:
            query.addBindValue(item.status.value)
            query.addBindValue(item.message)
            query.addBindValue(utils.date.to_iso(item.completed))
            query.addBindValue(item.pk)
            if not query.exec():
                con.rollback()
                err_msg = query.lastError().databaseText()
                critical_msg('error_batch_update', err_msg)
                return False
        con.commit()
        return True
    except Exception as e:
        critical_msg('error_batch_update E', str(e))
        con.rollback()
        return False


@db_logger
def completed_batch_update(transfer_items, con_name='con'):
    # Initiated by main thread
    con = QSqlDatabase.database(con_name)
    if not con.open():
        raise exceptions.DatabaseClosedException
    try:
        con.transaction()
        query = QSqlQuery(con)
        query.prepare('''
            UPDATE
                transfers
            SET
                status = (?), end_time = (?)
            WHERE
                pk = (?)
            ''')
        for item in transfer_items:
            query.addBindValue(item.status.value)
            query.addBindValue(utils.date.to_iso(item.completed))
            query.addBindValue(item.pk)
            if not query.exec():
                con.rollback()
                err_msg = query.lastError().databaseText()
                critical_msg('completed_batch_update', err_msg)
                return False
        con.commit()
        return True
    except Exception as e:
        critical_msg('completed_batch_update E', str(e))
        con.rollback()
        return False


@db_logger
def restart_queued_transfer(item, con_name='con'):
    # Initiated by main thread
    con = QSqlDatabase.database(con_name)
    if not con.open():
        raise exceptions.DatabaseClosedException
    try:
        con.transaction()
        query = QSqlQuery(con)
        query.prepare('''
            UPDATE
                transfers
            SET
                status = (?), start_time = ""
            WHERE
                pk = (?)
        ''')
        query.addBindValue(TransferStatus.PENDING.value)
        query.addBindValue(item.pk)
        if not query.exec():
            con.rollback()
            err_msg = query.lastError().databaseText()
            critical_msg('restart_queued_transfer', err_msg)
            return False
        con.commit()
        return True
    except Exception as e:
        critical_msg('restart_queued_transfer E', str(e))
        con.rollback()
        return False


def critical_msg(source, msg, parent=None):
    # This sould require a parent for blocking
    print(source, msg, sep=' | ')
    logging.critical(f'Database Error: {source} | {msg}')
    '''
    QMessageBox.critical(
        parent,
        'Error!',
        f'Database Error: {msg}'
    )
    '''


@db_logger
def clean_database(con_name='con'):
    con = QSqlDatabase.database(con_name)
    if not con.open():
        raise exceptions.DatabaseClosedException
    success = False
    try:
        _global_mutex.lock()
        if not con.exec('UPDATE transfers SET status = 0 WHERE status > 0'):
            err_msg = con.lastError().databaseText()
            critical_msg('cleaning', err_msg)
        else:
            if con.exec('''
                UPDATE
                    transfers
                SET
                    start_time = "", end_time = "", error_message = ""
            '''):
                success = True
            else:
                err_msg = con.lastError().databaseText()
                critical_msg('cleaning', err_msg)
    except Exception as e:
        critical_msg('clean_database E', str(e))
    finally:
        _global_mutex.unlock()
        return success


@db_logger
def setup(*, con_name='con'):
    con = sqlite3.connect(settings.DATABASE)
    cur = con.cursor()
    # Columns should only be for items that we want to keep on exit
    _ = cur.execute('''
        CREATE TABLE IF NOT EXISTS transfers (
            pk INTEGER PRIMARY KEY ASC,
            source TEXT NOT NULL,
            destination TEXT NOT NULL,
            size INTEGER NOT NULL,
            priority INTEGER DEFAULT 3,
            status INTEGER DEFAULT 0,
            start_time TEXT,
            end_time TEXT,
            error_message TEXT,
            source_type TEXT NOT NULL,
            destination_type TEXT NOT NULL
        );''')
    idx_check = cur.execute('''
        SELECT
            COUNT(*)
        FROM
            sqlite_master
        WHERE
            type='index' and name='idx_transfers_status'
    ''')
    if not idx_check.fetchone()[0]:
        _ = cur.execute(
            'CREATE INDEX idx_transfers_status on transfers (status)'
        )
    idx_check = cur.execute('''
        SELECT
            COUNT(*)
        FROM
            sqlite_master
        WHERE
            type='index' and name='idx_transfers_priority'
    ''')
    if not idx_check.fetchone()[0]:
        _ = cur.execute(
            'CREATE INDEX idx_transfers_priority on transfers (priority)'
        )
    _ = con.commit()
    _ = cur.execute('PRAGMA journal_mode=WAL;')
    _ = con.commit()


def flatten(item_destination_groups):
    for db_items, destination in item_destination_groups:
        for item in db_items:
            yield item, destination


@db_logger
def add_test_data(cwd=None, *, con_name='con'):
    con = sqlite3.connect(settings.DATABASE)
    cur = con.cursor()
    idx_check = cur.execute('''
        SELECT
            COUNT(*)
        FROM
            sqlite_master
        WHERE
            type='index' and name='idx_transfers_status'
    ''')
    if not idx_check.fetchone()[0]:
        raise Exception('Database has not been intiated.')
    batchsize = 0
    # for root, dirs, files in os.walk(cwd):
    for root, dirs, files in os.walk(os.path.expanduser('~')):
        for f in files:
            source = os.path.join(root, f)
            if not os.path.isfile(source):
                continue
            destination = f'{source}.DEST'
            size = os.stat(source).st_size
            _ = cur.execute('''
                INSERT INTO
                    transfers (source, destination, size)
                VALUES
                    (?, ?, ?)
            ''', (source, destination, size)
            )
            batchsize += 1
            if batchsize % 100 == 0:
                _ = con.commit()
    _ = con.commit()


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('cwd', nargs='?')
    parser.add_argument('--batchsize', default=5)
    args = parser.parse_args()

    setup()
    for i in range(1, int(args.batchsize) + 1):
        print(f'Batch {i} running...', end='', flush=True)
        add_test_data(args.cwd)
        print('DONE')
    con = sqlite3.connect(args.database_name)
    total_rows = con.execute('SELECT COUNT(*) FROM transfers').fetchone()[0]
    print(f'{total_rows:,} records found in the database.')
