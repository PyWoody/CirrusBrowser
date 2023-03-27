import json
import logging
import os


ROOT = os.path.abspath(os.path.dirname(__file__))
DATA_DIR = os.path.join(ROOT, 'data')
SETUP = os.path.join(DATA_DIR, 'setup.json')
DATABASE = os.path.join(DATA_DIR, 'transfers.db')
LOG = os.path.join(ROOT, 'logs', 'cirrus.log')


def transfer_window_visible():
    if os.path.isfile(SETUP):
        data = json.load(open(SETUP, 'r', encoding='utf8'))
        return data.get('Show Transer Window', False)
    return False


def update_transfer_window_status(status):
    if os.path.isfile(SETUP):
        data = json.load(open(SETUP, 'r', encoding='utf8'))
    else:
        data = dict()
    data['Show Transer Window'] = bool(status)
    with open(SETUP, 'w', encoding='utf8') as f:
        json.dump(data, f)


def append_panel(panel):
    if os.path.isfile(SETUP):
        data = json.load(open(SETUP, 'r', encoding='utf8'))
    else:
        data = dict()
    data.setdefault('Panel', []).append(panel)
    with open(SETUP, 'w', encoding='utf8') as f:
        json.dump(data, f)


def insert_panel(index, panel):
    if os.path.isfile(SETUP):
        data = json.load(open(SETUP, 'r', encoding='utf8'))
    else:
        data = dict()
    data.setdefault('Panel', []).insert(index, panel)
    with open(SETUP, 'w', encoding='utf8') as f:
        json.dump(data, f)


def saved_panels():
    if os.path.isfile(SETUP):
        data = json.load(open(SETUP, 'r', encoding='utf8'))
        yield from data.setdefault('Panel', [])


def update_saved_panels(panel):
    if os.path.isfile(SETUP):
        data = json.load(open(SETUP, 'r', encoding='utf8'))
    else:
        data = dict()
    for existing_panel in data.setdefault('Panel', []):
        if existing_panel['Type'] == panel['Type']:
            if existing_panel['Access Key'] == panel['Access Key']:
                for k, v in panel.items():
                    if existing_panel[k] != v:
                        existing_panel[k] = v
                break
    else:
        data.setdefault('Panel', []).append(panel)
    with open(SETUP, 'w', encoding='utf8') as f:
        json.dump(data, f)


def update_saved_panels_by_index(index, panel):
    if os.path.isfile(SETUP):
        data = json.load(open(SETUP, 'r', encoding='utf8'))
        try:
            data.setdefault('Panel', [])[index] = panel
        except IndexError:
            logging.debug(f'IndexError while updating Panel: {panel}')
        else:
            with open(SETUP, 'w', encoding='utf8') as f:
                json.dump(data, f)


def remove_saved_panel(index):
    if os.path.isfile(SETUP):
        data = json.load(open(SETUP, 'r', encoding='utf8'))
        try:
            data.setdefault('Panel', []).pop(index)
        except IndexError:
            logging.debug(f'IndexError while removing Panel: {data["Panels"]}')
        else:
            with open(SETUP, 'w', encoding='utf8') as f:
                json.dump(data, f)


def pop_saved_panel(panel):
    if os.path.isfile(SETUP):
        updated = False
        data = json.load(open(SETUP, 'r', encoding='utf8'))
        data.setdefault('Panel', []).reverse()
        try:
            data.setdefault('Panel', []).remove(panel)
        except ValueError:
            logging.debug(f'ValueError while popping Panel: {panel}')
        else:
            updated = True
        finally:
            data.setdefault('Panel', []).reverse()
        if updated:
            with open(SETUP, 'w', encoding='utf8') as f:
                json.dump(data, f)


def saved_users():
    if os.path.isfile(SETUP):
        data = json.load(open(SETUP, 'r', encoding='utf8'))
        yield from data.setdefault('Users', [])


def update_saved_users(user):
    if os.path.isfile(SETUP):
        data = json.load(open(SETUP, 'r', encoding='utf8'))
    else:
        data = dict()
    for existing_user in data.setdefault('Users', []):
        if existing_user['Type'] == user['Type']:
            if existing_user['Access Key'] == user['Access Key']:
                for k, v in user.items():
                    if existing_user[k] != v:
                        existing_user[k] = v
                break
    else:
        data.setdefault('Users', []).append(user)
    with open(SETUP, 'w', encoding='utf8') as f:
        json.dump(data, f)


def update_panel_by_index_cb(*, panel, index, key):
    def cb(value):
        panel[key] = value
        update_saved_panels_by_index(index, panel)
    return cb


def new_user(
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
