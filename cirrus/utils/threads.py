import threading


def assert_is_main_thread():
    assert threading.current_thread() is threading.main_thread()
