import logging

from functools import partial
from html.parser import HTMLParser

from . import date, files, threads

from PySide6.QtCore import Qt, QTimer, Slot
from PySide6.QtWidgets import QFrame


__all__ = ['date', 'files', 'threads']


class DataHTMLParser(HTMLParser):

    def __init__(self):
        super().__init__()
        self.text = ''

    def handle_data(self, data):
        self.text += data


class HLine(QFrame):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.HLine)
        self.setFrameShadow(QFrame.Sunken)


class VLine(QFrame):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.VLine)
        self.setFrameShadow(QFrame.Sunken)


@Slot(partial)
def execute_callback(func):
    try:
        return func()
    except Exception as e:
        logging.warn(f'Failed to execute {func!r} with error {e}')


@Slot(partial)
def execute_ss_callback(func):
    try:
        QTimer.singleShot(0, func)
    except Exception as e:
        logging.warn(f'Failed to execute {func!r} with error {e}')


class long_running_action:


    def __init__(self, wait=100, cursor=Qt.WaitCursor):
        self.wait = wait
        self.cursor = cursor
        self.timer_events_status = dict()
        self.orig_timer_event = None
        self.cls = None

    def __call__(self, func):
        def cb(*args, **kwargs):
            self.cls = args[0]
            if self.orig_timer_event is None:
                self.orig_timer_event = self.cls.timerEvent
            self.cls.timerEvent = self.timerEvent
            timer_id = self.cls.startTimer(self.wait)
            self.timer_events_status[timer_id] = False
            result = func(*args, **kwargs)
            QTimer.singleShot(0, partial(self.finished, timer_id))
            return result
        return cb

    def finished(self, timer_id):
        self.timer_events_status[timer_id] = True

    def restore(self):
        if not self.timer_events_status:
            self.cls.timerEvent = self.orig_timer_event

    def timerEvent(self, event):
        timer_id = event.timerId()
        completed = self.timer_events_status.get(timer_id)
        if completed is not None:
            if completed:
                if self.cls.cursor().shape() != Qt.ArrowCursor:
                    self.cls.setCursor(Qt.ArrowCursor)
                self.cls.killTimer(timer_id)
                del self.timer_events_status[timer_id]
                self.restore()
            else:
                if self.cls.cursor().shape() != self.cursor:
                    self.cls.setCursor(self.cursor)


def html_to_text(html):
    parser = DataHTMLParser()
    parser.feed(html)
    parser.close()
    return parser.text
