from PySide6.QtGui import QAction
from PySide6.QtCore import QRunnable


class BaseRunnable(QRunnable):

    def run(self, *args, **kwargs):
        raise NotImplementedError(
            'You must specifiy a slotted run() in the subclass'
        )


class BaseAction(QAction):

    def exec(self, *args, **kwargs):
        return True

    def runnable(self, *args, **kwargs):
        raise NotImplementedError(
            'You must specifiy runnable() in the subclass'
        )
