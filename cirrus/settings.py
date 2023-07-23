import json
import logging
import os

from PySide6.QtCore import QReadWriteLock

RW_LOCK = QReadWriteLock()

ROOT = os.path.abspath(os.path.dirname(__file__))
DATA_DIR = os.path.join(ROOT, 'data')
ICON_DIR = os.path.join(ROOT, 'icons')
SETUP = os.path.join(DATA_DIR, 'setup.json')
DATABASE = os.path.join(DATA_DIR, 'cirrus.db')
LOG = os.path.join(ROOT, 'logs', 'cirrus.log')


def read_settings_data(no_lock=False):
    if os.path.isfile(SETUP):
        if no_lock:
            data = json.load(open(SETUP, 'r', encoding='utf8'))
        else:
            RW_LOCK.lockForRead()
            data = json.load(open(SETUP, 'r', encoding='utf8'))
            RW_LOCK.unlock()
    else:
        data = dict()
    return data


def transfer_window_visible():
    data = read_settings_data()
    return data.get('Show Transer Window', False)


def update_transfer_window_status(status):
    RW_LOCK.lockForWrite()
    data = read_settings_data(no_lock=True)
    data['Show Transer Window'] = bool(status)
    with open(SETUP, 'w', encoding='utf8') as f:
        json.dump(data, f)
    RW_LOCK.unlock()


def append_panel(panel):
    RW_LOCK.lockForWrite()
    data = read_settings_data(no_lock=True)
    data.setdefault('Panels', []).append(panel)
    with open(SETUP, 'w', encoding='utf8') as f:
        json.dump(data, f)
    RW_LOCK.unlock()


def insert_panel(index, panel):
    RW_LOCK.lockForWrite()
    data = read_settings_data(no_lock=True)
    data.setdefault('Panels', []).insert(index, panel)
    with open(SETUP, 'w', encoding='utf8') as f:
        json.dump(data, f)
    RW_LOCK.unlock()


def saved_panels():
    if data := read_settings_data():
        yield from data.setdefault('Panels', [])


def update_saved_panels(panel):
    RW_LOCK.lockForWrite()
    data = read_settings_data(no_lock=True)
    for existing_panel in data.setdefault('Panels', []):
        if existing_panel['Type'] == panel['Type']:
            if existing_panel['Access Key'] == panel['Access Key']:
                for k, v in panel.items():
                    if existing_panel[k] != v:
                        existing_panel[k] = v
                break
    else:
        data.setdefault('Panels', []).append(panel)
    with open(SETUP, 'w', encoding='utf8') as f:
        json.dump(data, f)
    RW_LOCK.unlock()


def update_saved_panels_by_index(index, panel):
    if data := read_settings_data():
        try:
            RW_LOCK.lockForWrite()
            data.setdefault('Panels', [])[index] = panel
        except IndexError:
            logging.debug(f'IndexError while updating Panels: {panel}')
        else:
            with open(SETUP, 'w', encoding='utf8') as f:
                json.dump(data, f)
        finally:
            RW_LOCK.unlock()


def pop_saved_panel(index=-1):
    if data := read_settings_data():
        try:
            RW_LOCK.lockForWrite()
            _ = data.setdefault('Panels', []).pop(index)
        except IndexError:
            logging.debug(
                f'IndexError while removing Panels: {data["Panels"]}'
            )
        else:
            with open(SETUP, 'w', encoding='utf8') as f:
                json.dump(data, f)
        finally:
            RW_LOCK.unlock()


def remove_saved_panel(panel):
    if data := read_settings_data():
        updated = False
        data.setdefault('Panels', []).reverse()
        try:
            RW_LOCK.lockForWrite()
            data.setdefault('Panels', []).remove(panel)
        except ValueError:
            logging.debug(f'ValueError while popping Panels: {panel}')
        else:
            updated = True
        finally:
            data.setdefault('Panels', []).reverse()
            if updated:
                with open(SETUP, 'w', encoding='utf8') as f:
                    json.dump(data, f)
            RW_LOCK.unlock()


def saved_clients():
    if data := read_settings_data():
        yield from data.setdefault('Users', [])


def update_saved_clients(client):
    data = read_settings_data()
    RW_LOCK.lockForWrite()
    for existing_client in data.setdefault('Users', []):
        if existing_client['Type'] == client['Type']:
            if existing_client['Access Key'] == client['Access Key']:
                for k, v in client.items():
                    if existing_client[k] != v:
                        existing_client[k] = v
                break
    else:
        data.setdefault('Users', []).append(client)
    with open(SETUP, 'w', encoding='utf8') as f:
        json.dump(data, f)
    RW_LOCK.unlock()


def update_panel_by_index_cb(*, panel, index, key):
    def cb(value):
        panel[key] = value
        update_saved_panels_by_index(index, panel)
    return cb


def setup_client(
            *,
            act_type,
            root,
            access_key='N/A',
            nickname='',
            region='',
            endpoint_url='',
        ):
    # Need to re-think this name
    return {
        'Type': act_type,
        'Access Key': access_key,
        'Nickname': nickname,
        'Region': region,
        'Endpoint URL': endpoint_url,
        'Root': root,
    }
