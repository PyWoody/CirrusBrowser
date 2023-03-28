from .listings import (
    LocalFileListingWindow,
    S3FileListingWindow,
    DigitOceanFileListingWindow,
)


types = {
    'local': LocalFileListingWindow,
    's3': S3FileListingWindow,
    'digital ocean': DigitOceanFileListingWindow
}
