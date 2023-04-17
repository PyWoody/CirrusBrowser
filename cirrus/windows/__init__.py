from . import main
from .listings import (
    LocalFileListingWindow,
    S3FileListingWindow,
    DigitOceanFileListingWindow,
)


__all__ = ['main']


types = {
    'local': LocalFileListingWindow,
    's3': S3FileListingWindow,
    'digital ocean': DigitOceanFileListingWindow
}
