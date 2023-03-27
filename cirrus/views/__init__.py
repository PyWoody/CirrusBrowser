from .listings import LocalFileListing, S3FileListing, DigitalOceanFileListing

types = {
    'local': LocalFileListing,
    's3': S3FileListing,
    'digital ocean': DigitalOceanFileListing
}
