import hashlib
import logging
import os
import random
import threading
import time
import uuid


from cirrus.exceptions import ConflictException
from cirrus.items import TransferItem
from cirrus.statuses import TransferStatus
from PySide6.QtCore import (
    QObject,
    Signal,
    Slot,
)


class Executor(QObject):
    started = Signal()
    transfer_started = Signal(TransferItem)
    update = Signal(TransferItem)
    finished = Signal(TransferItem)
    stopped = Signal(TransferItem)
    completed = Signal()

    def __init__(self, db_queue,  parent=None, max_workers=None):
        super().__init__(parent)
        self.database_queue = db_queue
        self.database_queue.add_worker.connect(
            self.increase_max_worker_count
        )
        self.database_queue.remove_worker.connect(
            self.decrease_max_worker_count
        )
        self.thread_lock = threading.Lock()
        self.threads = []
        self.current_workers = 0
        self.max_workers = max_workers
        # Not great. May want to come from windows (?)
        # Shutdown needs to be handled better
        self.transfer_queue = None
        self.__stop = False

    def fill_thread_pool(self):
        while self.current_workers < self.max_workers:
            thread_uuid = str(uuid.uuid1())
            t = threading.Thread(
                target=self.run, name=thread_uuid, daemon=True
            )
            self.threads.append(t)
            t.start()
            self.increase_worker_count()
            logging.info(f'Initiated thread {self.current_workers}')

    @Slot()
    def start(self):
        self.__stop = False
        self.started.emit()
        self.database_queue.build_queue()
        if self.current_workers < self.max_workers:
            self.fill_thread_pool()
        for thread in self.threads:
            if not thread.is_alive() and not thread.ident:
                thread.start()
                logging.info(f'Started thread: {thread}')

    @Slot()
    def stop(self):
        self.__stop = True
        self.database_queue.stop()
        for thread in self.threads:
            if thread.is_alive():
                logging.info(f'Stopping thread: {thread}')
                thread.join(timeout=0.2)
                if thread.is_alive():
                    logging.info(f'Could not stop thread: {thread}')
                else:
                    logging.info(f'Stoped thread: {thread}')
            self.decrease_worker_count()
        self.threads.clear()
        self.completed.emit()

    def run(self):
        if self.__stop:
            return
        for transfer_item in self.database_queue.next_item():
            if self.__stop:
                self.stopped.emit(transfer_item)
                return
            transfer_item.status = TransferStatus.TRANSFERRING
            if skip_transfer(transfer_item):
                transfer_item.status = TransferStatus.COMPLETED
                transfer_item.message = 'Skipped'
                self.finished.emit(transfer_item)
            else:
                self.transfer_started.emit(transfer_item)
                self.process(transfer_item)
                if self.__stop:
                    if transfer_item.processed == transfer_item.size:
                        self.finished.emit(transfer_item)
                    else:
                        self.stopped.emit(transfer_item)
                    return
                else:
                    self.finished.emit(transfer_item)
        self.decrease_worker_count()  # semaphore or something
        self.completed.emit()

    def process(self, item):
        if self.__stop:
            item.status = TransferStatus.QUEUED
            item.message = 'Shutdown'
            return
        source = item.source
        upload_recv = item.destination.upload()
        try:
            upload_recv.send(None)
            for chunk in source.download():
                if self.__stop:
                    # TODO: Cleanup stuff
                    _ = upload_recv.send(None)  # Maybe
                    item.status = TransferStatus.QUEUED
                    item.message = 'Shutdown'
                    item.destination.remove()
                    return
                if written_amount := upload_recv.send(chunk):
                    item.processed += written_amount
            written_amount = upload_recv.send(None)
            upload_recv.close()
            item.processed += written_amount
        except Exception as e:
            item.status = TransferStatus.ERROR
            item.message = str(e)
        else:
            item.status = TransferStatus.COMPLETED
        finally:
            upload_recv.close()

    def _process(self, item):
        # This is a placeholder function for testing
        # bitrate = 10 * (1024 * 1024)
        # bitrate = 1024
        # bitrate = 10
        bitrate = 1
        # bitrate = .1
        completed = 0
        if skip_transfer(item):
            item.status = TransferStatus.COMPLETED
            item.message = 'Skipped'
            return
        while completed < item.size:
            if self.__stop:
                item.message = 'Shutdown'
                return
            completed += bitrate
            if completed > item.size:
                completed = item.size
            item.processed = completed
            bitrate += bitrate
            if random.randint(0, 1_000) % 333 == 0:
                item.status = TransferStatus.ERROR
                item.message = 'ERROR'
                return
            if completed != item.size:
                time.sleep(.5)
        item.status = TransferStatus.COMPLETED

    @Slot()
    def decrease_max_worker_count(self):
        with self.thread_lock:
            if self.max_workers >= 2:
                self.max_workers -= 1

    @Slot()
    def increase_max_worker_count(self):
        with self.thread_lock:
            self.max_workers += 1
        self.start()

    def decrease_worker_count(self):
        with self.thread_lock:
            if self.current_workers > 0:
                self.current_workers -= 1

    def increase_worker_count(self):
        with self.thread_lock:
            self.current_workers += 1

    def shutdown(self):
        self.__stop = True
        self.database_queue.stop()
        if not self.database_queue.join():
            logging.warn('Could not stop database_queue')
        self.stop()


def skip_transfer(transfer_item):
    # Terrible name
    """If the TransferItem.conflict is 'overwrite', returns True.

    Otherwise, checks if the TransferItem.destination already exists in its
    respective location. If so, compares the existing destination
    file against the TransferItem.source file information.

    The supplied conflict resolution in the TransferItem.conflict
    will be used.

    The function will return True if the transfer should skipped; else, False

    For convenience, the comparison strings are:
        - overwrite
        - hash
        - size
        - newer
        - rename
        - skip
    """
    if transfer_item.conflict == 'overwrite':
        # Skip all checks
        return False
    if not transfer_item.destination.exists:
        return False
    else:
        if transfer_item.conflict == 'skip':
            return True
    if transfer_item.conflict == 'hash':
        # TODO: Add logging/status indicator updates as s3/DO may take a while
        # TODO: Change the TransferItems 'rate' to 'Checking hash...'
        source_hash_md5 = hashlib.md5()
        for chunk in transfer_item.source.download():
            source_hash_md5.update(chunk)
        dest_hash_md5 = hashlib.md5()
        for chunk in transfer_item.destination.download():
            dest_hash_md5.update(chunk)
        return source_hash_md5.hexdigest() == dest_hash_md5.hexdigest()
    if transfer_item.conflict == 'size':
        return transfer_item.source.size == transfer_item.destination.size
    if transfer_item.conflict == 'newer':
        return transfer_item.source.mtime <= transfer_item.destination.mtime
    if transfer_item.conflict == 'rename':
        client_copy = transfer_item.destination.client.copy()
        root, fname = os.path.split(transfer_item.destination.root)
        version = 0
        while transfer_item.destination.exists:
            version += 1
            client_copy['Root'] = os.path.join(
                root,
                f' ({version})'.join(os.path.splitext(fname))
            )
            new_item = transfer_item.destination.create(
                client_copy,
                size=transfer_item.destination.size,
                is_dir=transfer_item.destination.is_dir,
                mtime=transfer_item.destination.mtime,
                ctime=transfer_item.destination.ctime,
            )
            transfer_item.destination = new_item
        return False
    raise ConflictException(str(transfer_item))
