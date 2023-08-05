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


def find_parent(self, parent_type):
    if parent := self.parent():
        if parent is self:
            return
        if type(parent) == parent_type:
            return parent
        return find_parent(parent, parent_type)


class long_running_action:

    timer_events = dict()

    def __init__(self, wait=100, cursor=Qt.WaitCursor):
        self.wait = wait
        self.cursor = cursor
        self.cls = None

    def __call__(self, func):
        def cb(*args, **kwargs):
            self.cls = args[0]
            orig_timer_event = self.cls.timerEvent
            self.cls.timerEvent = self.timerEvent
            timer_id = self.cls.startTimer(self.wait)
            self.timer_events[timer_id] = (orig_timer_event, False)
            result = func(*args, **kwargs)
            QTimer.singleShot(
                0, partial(self.finished, orig_timer_event, timer_id)
            )
            return result
        return cb

    def finished(self, orig_timer, timer_id):
        self.timer_events[timer_id] = (orig_timer, True)

    def timerEvent(self, event):
        timer_id = event.timerId()
        if running_event := self.timer_events.get(timer_id):
            orig_timer, completed = running_event
            if completed:
                if self.cls.cursor().shape() != Qt.ArrowCursor:
                    self.cls.setCursor(Qt.ArrowCursor)
                self.cls.killTimer(timer_id)
                self.cls.timerEvent = orig_timer
                del self.timer_events[timer_id]
            else:
                if self.cls.cursor().shape() != self.cursor:
                    self.cls.setCursor(self.cursor)


def html_to_text(html):
    parser = DataHTMLParser()
    parser.feed(html)
    parser.close()
    return parser.text
