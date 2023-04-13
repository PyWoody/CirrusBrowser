from PySide6.QtGui import QAction
from PySide6.QtCore import QRunnable, Signal


class BaseRunnable(QRunnable):

    def run(self, *args, **kwargs):
        raise NotImplementedError(
            'You must specifiy a slotted run() in the subclass'
        )


class BaseAction(QAction):
    accepted = Signal()

    def show_dialog(self, *args, **kwargs):
        return False

    def runnable(self, *args, **kwargs):
        raise NotImplementedError(
            'You must specifiy runnable() in the subclass'
        )
