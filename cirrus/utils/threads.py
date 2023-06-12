from functools import wraps
import threading


def assert_is_main_thread():
    assert threading.current_thread() is threading.main_thread()


def decorator_assert_is_main_thread(func):
    @wraps(func)
    def cb(*args, **kwargs):
        assert_is_main_thread()
        result = func(*args, **kwargs)
        return result
    return cb
