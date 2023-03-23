from functools import partial

from PySide6.QtCore import QObject, Signal


class ActionSignals(QObject):

    aborted = Signal()
    error = Signal(str)
    finished = Signal(str)
    process_queue = Signal()
    callback = Signal(partial)
    select = Signal()
    started = Signal(str)
    update = Signal(str)
