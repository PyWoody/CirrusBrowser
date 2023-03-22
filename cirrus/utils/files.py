import re


def bytes_to_human(size):
    gb = 1024 * 1024 * 1024
    mb = 1024 * 1024
    kb = 1024
    if size > gb:
        return f'{size / gb:.2f} GB'
    elif size > mb:
        return f'{size / mb:.2f} MB'
    elif size > kb:
        return f'{size / kb:.2f} KB'
    if size < 1:
        size = '<1'
    return f'{size} bytes'


def human_to_bytes(num_size):
    size_re = re.compile(r'^([\d\.]*)\s?([A-Z]*)')
    if search := re.search(size_re, num_size):
        num, size = search.groups()
        num = float(num)
        if size == 'GB':
            return num * (1024 * 1024 * 1024)
        if size == 'MB':
            return num * (1024 * 1024)
        if size == 'KB':
            return num * 1024
        if size == 'B':
            return num
    raise ValueError(num_size)
