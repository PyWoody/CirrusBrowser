import os

from PySide6.QtGui import QValidator


class LocalPathValidator(QValidator):

    def __init__(self, initial_path='', parent=None):
        super().__init__(parent)
        self.last_valid_path = initial_path

    def validate(self, input_text, pos):
        if os.path.isdir(input_text):
            self.last_valid_path = input_text
            return QValidator.Acceptable
        return QValidator.Intermediate

    def fixup(self, input_text):
        if not os.path.isdir(input_text) and self.last_valid_path:
            return self.last_valid_path
        return ''


class S3PathValidator(QValidator):

    def __init__(self, initial_path='', parent=None):
        super().__init__(parent)
        self.last_valid_path = initial_path

    def validate(self, input_text, pos):
        if os.path.isdir(input_text):
            self.last_valid_path = input_text
            return QValidator.Acceptable
        return QValidator.Intermediate

    def fixup(self, input_text):
        if not os.path.isdir(input_text) and self.last_valid_path:
            return self.last_valid_path
        return ''


class NumberValidator(QValidator):

    def validate(self, input_text, pos):
        if input_text.isdigit():
            return QValidator.Acceptable
        return QValidator.Invalid
