from PySide6.QtGui import QAction
from PySide6.QtCore import QRunnable, Slot, Signal


class BaseRunnable(QRunnable):

    def run(self, *args, **kwargs):
        raise NotImplementedError(
            'You must specifiy a slotted run() in the subclass'
        )


class BaseAction(QAction):
    accepted = Signal()

    @Slot(str, bool)
    def update_conflict(self, conflict, checked):
        """Updates the Action's conflict value to the specified `conflict`
        Useful for connecting to the Dialog's .toggled signal
        """
        if checked:
            self.conflict = conflict

    def show_dialog(self, *args, **kwargs):
        return False

    def runnable(self, *args, **kwargs):
        raise NotImplementedError(
            'You must specifiy runnable() in the subclass'
        )
