import boto3
import logging
import mimetypes
import os
import shutil
import threading

from cirrus import utils
from cirrus.exceptions import CallbackError, ItemIsNotADirectory
from cirrus.statuses import TransferStatus, TransferPriority
from cirrus.s3stream import S3StreamingDownload, S3StreamingUpload

import keyring

from botocore.config import Config
from boto3.s3.transfer import TransferConfig


# TODO: "user" is incredibly confusing and non-ituitive.
#       data? metdata? info? settings? client (+1)?

# NOTE: row is obviously wrong


class TransferItem:

    __slots__ = (
        'pk',
        'row',
        'source',
        'destination',
        'size',
        'message',
        'processed',
        'priority',
        # 'progress',
        '__status',
        'started',
        'completed',
    )

    def __init__(
                self,
                pk,
                source,
                destination,
                size,
                processed=0,
                progress=0,
                priority=TransferPriority.NORMAL,
                status=TransferStatus.PENDING,
                message='Queued',
                started=None,
            ):
        self.pk = pk
        self.row = pk - 1
        self.source = source
        self.destination = destination
        self.size = size
        self.processed = processed
        self.__status = status
        self.started = started
        self.message = message
        self.priority = priority
        self.completed = None

    def __gt__(self, other):
        return self.pk > other.pk

    def __lt__(self, other):
        return self.pk < other.pk

    def __repr__(self):
        return (
            f'{self.__class__.__name__}(pk={self.pk}, row={self.row}, '
            f'source="{self.source}", '
            f'destination="{self.destination}", size={self.size}, '
            f'message="{self.message}", processed={self.processed}, '
            f'priority={self.priority},  status={self.status}, '
            f'''started={'"' if self.started else ""}{self.started}'''
            f'''{'"' if self.started else ""}, '''
            f'''completed={'"' if self.completed else ""}{self.completed}'''
            f'''{'"' if self.completed else ""})'''
        )

    @property
    def status(self):
        return self.__status

    @status.setter
    def status(self, status):
        if status.value <= TransferStatus.TRANSFERRING.value:
            # Reset started to allow for restarteding transfers
            self.started = utils.date.now()
            self.completed = None
        elif status == TransferStatus.COMPLETED:
            self.completed = utils.date.now()
        elif status == TransferStatus.ERROR:
            self.completed = utils.date.now()
        elif not isinstance(status, TransferStatus):
            raise AttributeError(
                'TrasferItem.status must be of the Status Enum class'
            )
        self.__status = status

    @property
    def progress(self):
        try:
            return (self.processed / self.size) * 100
        except ZeroDivisionError:
            return 0

    @property
    def time_delta(self):
        """Returns a datetime.utcnow object from queue's started"""
        if self.completed:
            return self.completed - self.started
        return utils.date.now() - self.started

    @property
    def rate(self):
        """Returns a human readable upload rate per second"""
        rate = self.rate_in_bytes()
        rate_for_humans = utils.files.bytes_to_human(rate)
        return f'{rate_for_humans}/s'

    def rate_in_bytes(self):
        """Returns upload rate in bytes per second"""
        if not self.processed:
            return 0
        if seconds := self.time_delta.seconds:
            return self.processed // seconds
        return self.processed


class LocalItem:

    __slots__ = ('user', 'root', 'is_dir', 'size', 'mtime', 'ctime')

    def __init__(self, user, *, size=0, is_dir=False, mtime=0, ctime=0):
        if root := user.get('Root'):
            self.root = root
        else:
            self.root = os.path.expanduser('~')
        self.user = user
        self.is_dir = is_dir
        self.size = size
        self.mtime = mtime
        self.ctime = ctime

    def __repr__(self):
        return (f'{self.__class__.__name__}('
                f'{self.user}, '
                f'size={self.size}, '
                f'is_dir={self.is_dir}, '
                f'mtime={self.mtime}, '
                f'ctime={self.ctime})')

    @property
    def type(self):
        return 'local'

    @classmethod
    def create(cls, user, *, size=0, is_dir=False):
        return cls(user, size=size, is_dir=is_dir)

    def clean(self, path):
        return path.replace('/', os.sep).replace('\\', os.sep)

    def listdir(self, path=None):
        if not self.is_dir:
            raise ItemIsNotADirectory
        if path is None:
            path = self
        for root, dirs, files in os.walk(path.root):
            _user = new_user(self.user, root)
            root_item = self.create(_user, is_dir=True)
            dir_items = []
            for d in dirs:
                _user = new_user(self.user, os.path.join(root, d))
                dir_items.append(self.create(_user, is_dir=True))
            file_items = []
            for f in files:
                fname = os.path.join(root, f)
                _user = new_user(self.user, fname)
                size = os.stat(fname).st_size
                item = self.create(_user, size=size)
                file_items.append(item)
            yield root_item
            yield from dir_items
            yield from file_items
            return

    def makedirs(self, exist_ok=True):
        if not self.is_dir:
            raise ItemIsNotADirectory
        try:
            os.makedirs(self.root, exist_ok=exist_ok)
        except Exception as e:
            raise e

    def walk(self, path=None):
        if not self.is_dir:
            raise ItemIsNotADirectory
        if path is None:
            path = self
        for root, dirs, files in os.walk(path.root):
            _user = new_user(self.user, root)
            root_item = self.create(_user, is_dir=True)
            dir_items = []
            for d in dirs:
                _user = new_user(self.user, os.path.join(root, d))
                dir_items.append(self.create(_user, is_dir=True))
            file_items = []
            for f in files:
                fname = os.path.join(root, f)
                if os.path.isfile(fname):
                    _user = new_user(self.user, fname)
                    size = os.stat(fname).st_size
                    item = self.create(_user, size=size)
                    file_items.append(item)
            yield root_item, dir_items, file_items

    def upload(self, callback=None, overwrite=False, buffer_size=4096):
        try:
            if not overwrite and os.path.isfile(self.root):
                raise FileExistsError
            written_amount = 0
            data = b''
            os.makedirs(os.path.dirname(self.root), exist_ok=True)
            with open(self.root, 'wb') as f:
                while True:
                    chunk = yield written_amount
                    if chunk is None:
                        written_amount = f.write(data)
                    else:
                        data += chunk
                        if len(data) >= buffer_size:
                            written_amount = f.write(data)
                            data = b''
                        else:
                            written_amount = 0
        except GeneratorExit:
            if callback:
                try:
                    callback()
                except CallbackError as e:
                    raise CallbackError('Callback failed') from e
        except Exception as e:
            print(e)
            raise e

    def remove(self, callback=None):
        def rmtree_cb(function, path, excinfo):
            logging.warn(f'Checking if {path} exists')
            if os.path.isdir(path):
                try:
                    os.rmdir(path)
                except OSError:
                    logging.error(f'Could not remove {path}')
                except FileNotFoundError:
                    pass
            elif os.path.isfile(path):
                try:
                    os.remove(path)
                except FileNotFoundError:
                    pass
                except Exception as e:
                    logging.error(f'Could not remove {path}: {e!r}')

        if not os.path.exists(self.root):
            logging.info(f'{self.root} does not exist')
        else:
            try:
                if self.is_dir:
                    shutil.rmtree(self.root, onerror=rmtree_cb)
                    response = f'Removed all items under {self.root}'
                else:
                    os.remove(self.root)
                    response = f'Removed {self.root}'
            except Exception as e:
                print(e)
                raise e
            else:
                logging.info(response)

    def download(self, callback=None):
        try:
            with open(self.root, 'rb') as f:
                for chunk in f:
                    yield chunk
        except Exception as e:
            raise e
        else:
            if callback:
                try:
                    callback()
                except CallbackError as e:
                    raise CallbackError('Callback failed') from e


class BaseS3Item:

    def __init__(
        self, user, *, size=0, mtime=0, is_dir=False, collapsed=True
    ):
        if not user['Root'].startswith('/'):
            user['Root'] = '/' + user['Root']
        self.root = user['Root']
        self.user = user
        self.is_dir = is_dir
        self.collapsed = collapsed
        self.size = size
        self.mtime = mtime
        self.ctime = mtime
        self.config = None

    def __repr__(self):
        return (f'{self.__class__.__name__}('
                f'{self.user}, '
                f'size={self.size}, '
                f'collapsed={self.collapsed}, '
                f'is_dir={self.is_dir}, '
                f'mtime={self.mtime})')

    def setup_client(self, *args, **kwargs):
        raise NotImplementedError('Must be specified in sub-class')

    @classmethod
    def create(cls, user, *, size=0, is_dir=False, collapsed=True):
        return cls(
            user=user,
            size=size,
            is_dir=is_dir,
            collapsed=collapsed,
        )

    @classmethod
    def create_from_content(cls, user, *, bucket, content):
        root = '/'.join(
            [bucket, content.get('Key', content.get('Prefix'))]
        )
        size = content.get('Size', 0)
        _user = new_user(user, root)
        return cls(
            _user,
            size=size,
            is_dir=True if size == 0 else False,
            mtime=content.get('LastModified', 0),
        )

    @property
    def bucket(self):
        return self.root.lstrip('/').split('/')[0]

    @property
    def key(self):
        return '/'.join(self.root.lstrip('/').split('/')[1:]).lstrip('/')

    @property
    def space(self):
        if self.is_dir:
            output = '/'.join(
                self.root.lstrip('/').split('/')[1:]
            ).lstrip('/').rstrip('/') + '/'
            if output != '/':
                return output
        else:
            *root, _ = self.key.split('/')
            if len(root) >= 2:
                return '/'.join(root).lstrip('/').rstrip('/') + '/'

    def clean(self, path):
        return path.replace('\\', '/')

    def makedirs(self, exist_ok=True):
        if not self.is_dir:
            raise ItemIsNotADirectory
        try:
            client = self.setup_client()
            response = client.put_object(
                    Key=self.space,
                    Bucket=self.bucket,
                    Body=b'',
                )
        except Exception as e:
            logging.warn(response)
            raise e

    def walk(self, root=None, topdown=True):
        if not self.is_dir:
            raise ItemIsNotADirectory
        if root is None:
            root = self
        client = self.setup_client()
        yield from self.__walk(client=client, path=root, topdown=topdown)

    def __walk(self, *, client, path, topdown=True):
        dirs, files = [], []
        for item in self.listdir(client=client, path=path.root.lstrip('/')):
            if item.is_dir:
                dirs.append(item)
            else:
                files.append(item)
        yield path, dirs, files
        for dir_item in dirs:
            dir_name = dir_item.root.strip('/').split('/')[-1]
            out_path = f'{path.root.rstrip("/")}/{dir_name}/'
            _user = new_user(self.user, out_path)
            out_item = self.create(_user, is_dir=True)
            yield from self.__walk(
                client=client, path=out_item, topdown=topdown
            )

    def listdir(self, *, client=None, path=None):
        if not self.is_dir:
            raise ItemIsNotADirectory
        if client is None:
            client = self.setup_client()
        client_config = self.config.copy()
        if path is None:
            bucket = self.bucket
            space = self.space
        else:
            bucket, *space = path.strip('/').split('/')
            space = '/'.join(space) if space else None
        if bucket != client_config.get('Bucket'):
            client_config['Bucket'] = bucket
        if space is None and client_config.get('Prefix'):
            del client_config['Prefix']
        elif space != client_config.get('Prefix'):
            client_config['Prefix'] = space.rstrip('/') + '/'
        response = client.list_objects_v2(**client_config)
        for content in response.get('CommonPrefixes', []):
            yield self.create_from_content(
                self.user, bucket=bucket, content=content
            )
        for content in response.get('Contents', []):
            yield self.create_from_content(
                self.user, bucket=bucket, content=content
            )
        while response.get('IsTruncated'):
            client_config['ContinuationToken'] = response['NextContinuationToken']
            response = client.list_objects_v2(**client_config)
            for content in response.get('CommonPrefixes', []):
                yield self.create_from_content(
                    self.user, bucket=bucket, content=content
                )
            for content in response.get('Contents', []):
                yield self.create_from_content(
                    self.user, bucket=bucket, content=content
                )

    def upload(self, callback=None, overwrite=False, buffer_size=4096):
        c_type, _ = mimetypes.guess_type(self.key)
        if c_type is None:
            c_type = 'application/octet-stream'
            logging.warn(
                (f'No guessable ContenType found for {self.key}. '
                 'Using "application/octet-stream" instead.')
            )
        extra_args = {
            'ACL': 'public-read',
            'ContentType': c_type,
        }
        file_obj = S3StreamingUpload(self.size)
        t = threading.Thread(
            target=self.__upload,
            args=(file_obj, extra_args),
            daemon=True
        )
        t.start()
        written_amount = 0
        write_size = 4096
        min_write_size = write_size
        max_write_size = write_size * 20
        data = b''
        try:
            while True:
                chunk = yield written_amount
                if err := file_obj.error:
                    logging.info(
                        f'Propogating error ({str(err)}) from {file_obj!r}'
                    )
                    raise err
                elif chunk is None:
                    written_amount = file_obj.write(data)
                    file_obj.close()
                    t.join()
                else:
                    data += chunk
                    if len(data) >= min_write_size:
                        written_amount = file_obj.write(data)
                        data = b''
                        if min_write_size < max_write_size:
                            min_write_size += write_size
                    else:
                        written_amount = 0
        except GeneratorExit:
            if callback:
                try:
                    callback()
                except CallbackError as e:
                    raise CallbackError('Callback failed') from e
        except Exception as e:
            raise e

    def __upload(self, file_obj, extra_args):
        client = self.setup_client()
        transfer_config = TransferConfig(use_threads=False)
        try:
            client.upload_fileobj(
                file_obj,
                self.bucket,
                self.key,
                ExtraArgs=extra_args,
                Config=transfer_config,
                Callback=file_obj.prune
            )
        except Exception as e:
            # TODO: Notify file_obj it's failed. Set err msg. Close.
            logging.info(f'Error in __upload: {str(e)}')
            file_obj.error = e

    def remove(self, callback=None):
        client = self.setup_client()
        try:
            if self.is_dir:
                # TODO: Must delete everything in the bucket first
                #       then, only when the bucket is empty, can you delete it
                raise NotImplementedError
                response = client.delete_bucket(Bucket=self.bucket)
                # TODO: bottom-up so it can do files > dirts
                for root_item, dir_items, file_items in self.walk():
                    pass
            else:
                response = client.delete_object(
                    Bucket=self.bucket,
                    Key=self.key
                )
        except Exception as e:
            print(e)
            raise e
        else:
            logging.info(f'{response!r}')

    def download(self, callback=None):
        file_obj = S3StreamingDownload(self.size)
        t = threading.Thread(
            target=self.__download,
            args=(file_obj,),
            daemon=True
        )
        try:
            t.start()
            for chunk in file_obj:
                yield chunk
            t.join()
        except Exception as e:
            raise e
        else:
            if callback:
                try:
                    callback()
                except CallbackError as e:
                    raise CallbackError('Callback failed') from e

    def __download(self, file_obj):
        client = self.setup_client()
        transfer_config = TransferConfig(use_threads=False)
        try:
            client.download_fileobj(
                self.bucket,
                self.key,
                file_obj,
                Config=transfer_config,
            )
        except Exception as e:
            # TODO: Notify file_obj it's failed. Set err msg. Close.
            logging.info(f'Error in __download: {str(e)}')
            file_obj.error = e


class S3Item(BaseS3Item):

    __slots__ = (
        'user',
        'root',
        'is_dir',
        'collapsed',
        'size',
        'config',
        'mtime',
        'ctime'
    )

    @property
    def type(self):
        return 's3'

    def setup_client(self, max_keys=1_000):
        retry_config = Config(
            retries={'max_attempts': 10, 'mode': 'standard'}
        )
        self.config = {
                'Bucket': self.bucket,
                'MaxKeys': max_keys,
                'Delimiter': '/',
            }
        if self.space is not None:
            self.config['Prefix'] = self.space
        session = boto3.session.Session()
        return session.client(
                's3',
                region_name=self.user['Region'],
                aws_access_key_id=self.user['Access Key'],
                aws_secret_access_key=keyring.get_password(
                    'system', f'_s3_{self.user["Access Key"]}_secret_key'
                ),
                config=retry_config,
            )


class DigitalOceanItem(BaseS3Item):

    __slots__ = (
        'user',
        'root',
        'is_dir',
        'collapsed',
        'size',
        'config',
        'mtime',
        'ctime'
    )

    @property
    def type(self):
        return 'digital ocean'

    def setup_client(self, max_keys=1_000):
        retry_config = Config(
            retries={'max_attempts': 10, 'mode': 'standard'}
        )
        self.config = {
                'Bucket': self.bucket,
                'MaxKeys': max_keys,
                'Delimiter': '/',
            }
        if self.space is not None:
            self.config['Prefix'] = self.space
        session = boto3.session.Session()
        return session.client(
                's3',
                region_name=self.user['Region'],
                endpoint_url=self.user['Endpoint URL'],
                aws_access_key_id=self.user['Access Key'],
                aws_secret_access_key=keyring.get_password(
                    'system', f'_s3_{self.user["Access Key"]}_secret_key'
                ),
                config=retry_config,
            )


def new_user(user, root):
    # Need to rethink this name
    _user = user.copy()
    _user['Root'] = root
    return _user


def account_to_item(account):
    if account['Type'] == 'S3':
        return S3Item(account.copy(), is_dir=True)
    if account['Type'] == 'Digital Ocean':
        return DigitalOceanItem(account.copy(), is_dir=True)
    elif account['Type'] == 'Local':
        return LocalItem(account.copy(), is_dir=True)
    else:
        raise ValueError(f'No Item-type for {account["Type"]}')


def match_user(users, act_type, root):
    for user in users:
        if user['Type'].lower() == act_type.lower():
            if len(os.path.commonprefix([user['Root'], root])) > 1:
                _user = user.copy()
                return _user


types = {'local': LocalItem, 's3': S3Item, 'digital ocean': DigitalOceanItem}
