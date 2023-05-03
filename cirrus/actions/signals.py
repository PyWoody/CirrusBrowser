from functools import partial

from PySide6.QtCore import QObject, Signal


class ActionSignals(QObject):

    aborted = Signal()
    accepted = Signal()
    callback = Signal(partial)
    ss_callback = Signal(partial)
    error = Signal(str)
    finished = Signal(str)
    process_queue = Signal()
    select = Signal()
    started = Signal()
    update = Signal(str)
