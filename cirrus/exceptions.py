class DatabaseClosedException(Exception):
    pass


class ItemIsNotADirectory(Exception):
    pass


class CallbackError(Exception):
    pass


class ConflictException(Exception):
    pass


class UnexpectedItemTypeException(Exception):
    pass
