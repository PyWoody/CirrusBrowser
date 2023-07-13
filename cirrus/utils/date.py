import datetime

from PySide6.QtCore import QDateTime, Qt


TIMEZONE = datetime.datetime.now(datetime.timezone.utc).astimezone().tzinfo


def epoch():
    return datetime.datetime(1970, 1, 1, tzinfo=TIMEZONE)


def now():
    return datetime.datetime.now(tz=TIMEZONE)


def iso_now():
    return now().isoformat()


def to_iso(timestamp):
    return timestamp.isoformat()


def qdatetime_to_iso(timestamp):
    return datetime.datetime.fromisoformat(
        timestamp.toString(Qt.ISODate)
    )


def period_to_seconds(period, amount):
    # Period == day or whatever. Need to re-name this
    period = period.strip().lower()
    amount = int(amount)
    if period == 'minutes':
        return amount * 60
    elif period == 'hours':
        return amount * 60 * 60
    elif period == 'days':
        return (amount * 60 * 60) * 24
    else:
        raise ValueError(f'{period} not a valid option')


def subtract_period(period, amount, date=None):
    if date is None:
        date = now()
    period = period.strip().lower()
    amount = int(amount)
    if period == 'seconds':
        return date - datetime.timedelta(seconds=amount)
    elif period == 'minutes':
        return date - datetime.timedelta(minutes=amount)
    elif period == 'hours':
        return date - datetime.timedelta(hours=amount)
    elif period == 'days':
        return date - datetime.timedelta(days=amount)
    else:
        raise ValueError(f'{period} not a valid option')


if __name__ == '__main__':
    print(f'The local tzinfo is {TIMEZONE}')
    print(f'The now datetime is {repr(now())}')
    print(f'The now isoformat datetime is {iso_now()}')
