from .listings import (
    LocalFileListingView,
    S3FileListingView,
    DigitalOceanFileListingView,
)

types = {
    'local': LocalFileListingView,
    's3': S3FileListingView,
    'digital ocean': DigitalOceanFileListingView,
}
