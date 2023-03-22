import logging

from functools import partial
from html.parser import HTMLParser

from . import date, files, threads

from PySide6.QtCore import Slot
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


@Slot(partial)
def execute_callback(func):
    try:
        return func()
    except Exception as e:
        logging.warn(f'Failed to execute {func!r} with error {e}')


def html_to_text(html):
    parser = DataHTMLParser()
    parser.feed(html)
    parser.close()
    return parser.text
