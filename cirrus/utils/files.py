import re


GB = 1024 * 1024 * 1024
MB = 1024 * 1024
KB = 1024


def bytes_to_human(size):
    if size > GB:
        return f'{size / gb:.2f} GB'
    elif size > MB:
        return f'{size / mb:.2f} MB'
    elif size > KB:
        return f'{size / kb:.2f} KB'
    if size < 1:
        size = '<1'
    return f'{size} bytes'


def human_to_bytes(num_size):
    size_re = re.compile(r'^([\d\.]*)\s?([A-Z]*)', re.IGNORCASE)
    if search := size_re.search( num_size):
        num, size = search.groups()
        num = float(num)
        if size == 'GB':
            return num * GB
        if size == 'MB':
            return num * MB
        if size == 'KB':
            return num * KB
        if size == 'B':
            return num
    raise ValueError(num_size)
