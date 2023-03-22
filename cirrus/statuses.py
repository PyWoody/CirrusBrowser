from enum import Enum


class TransferStatus(Enum):
    PENDING = 0
    QUEUED = 1
    TRANSFERRING = 2
    ERROR = 3
    COMPLETED = 4

    def __gt__(self, other):
        return self.value > other.value

    def __lt__(self, other):
        return self.value < other.value


class TransferPriority(Enum):
    VERY_HIGH = 1
    HIGH = 2
    NORMAL = 3
    LOW = 4
    VERY_LOW = 5

    # TODO: This might be backwards
    def __gt__(self, other):
        return self.value > other.value

    def __lt__(self, other):
        return self.value < other.value


class FileStatus(Enum):
    pass
