# Cirrus Browser
## Experimental file manager for S3-like systems

The Cirrus Browser is a work-in-progress experimental file manager for S3-like systems. It supports uploading, downloading, and removing files from your preferred hosting provider.
<br />
<br />
### Features
---
**All Transfers are done in-memory without touching the underlying file system**

Transfers will all be performed using in-memory buffers with no unnecessary read/writes on the file system. Transfers begin immediately as soon as the first packet is sent.
<br />
<br />
**Transfer to multiple destinations at once**

Toggle available destinations to Transfer files to multiple destinations at once.
<br />
<br />
**Filter files to be transferred**

No need to create temporary directories just to transfer a subset of the files. Transfers support selectively filtering the source items to the destinations. The available filters are by filename, filetype, creation/modification times, and size.

Upload all of your .PNGs that were modified in the past two days and are over 10MB, for instance.
<br />
<br />
**Fast iterative search in multiple locations yields results immediately as the occur**

The iterative approach to search will yield results immediately as they are found. From the Search Results Window, you can easily Stop the search, Delete the selected results, or Download the selected results to the selected destinations.

Searching in multiple locations at once is supported.
<br />
<br />
### Installation
---

Requires `PySide6` for GUI, `boto3` for S3 compatibility, and `keyring` for securely storing credentials.

Note, PySide6 can be finicky to install. I would suggest following the official installation instructions before attempting to install the requirements.txt file.

```python3
python3 -m pip install -U pip
python3 -m pip install -r requirements.txt
```
<br />
<br />

### Running
---
Binaries are not available at this time. You will need to launch from the terminal.

```python3
python3 -m cirrus
```
<br />
<br />

### Screenshots
---

**Drag-and-Drop**

*Panel-to-Panel*

*From the File System*
<br />
<br />
**Searching**

*Multiple Locations*

*Recursive*

*Modifying Results*
<br />
<br />
**Transfers**

*Multiple destinations*

*Filtering*
