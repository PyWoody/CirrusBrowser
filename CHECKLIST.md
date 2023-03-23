## FEATURES:
- Encrypted credentials
- Server-to-Server (aka, buckets)
- cli w/ optional Rich
- Updated metadata/permissions
- Download
- Upload
    - Upload from zip-like files
- Search
    - Quick search
    - Extended search
    - Update file, directory attributes recursively accoridng to predefined rules
    - Download items recursively accoridng to predefined rules

---
## Progress:
### GUI
 - [ ] Main Window
 - [X] Encrypted Login/Credentials
 - [ ] Transfers Window
 - [ ] Settings Window
 - [ ] Basic Search Window
 - [ ] Quick Search Window
 - [X] Advanced Search Window
 - [ ] History Window

### CLI
 - [ ] Basic functionality
 - [ ] Verbose
 - [ ] Expressive GUI w/ Rich
 - [ ] Restartable and idempotent queues

### Thread Class
 - [X] Rate limiting
 - [ ] Pooling Queues
 - [ ] Pause/Resume
 - [ ] Graceful exit

### Multiprocessing Server
 - [ ] Starting
 - [ ] Stopping
 - [ ] Sharing Queue
 - [ ] Named Pools
 - [ ] Graceful exit

### Search
 - [ ] Basic Search
 - [ ] Quick Search (`/`)
 - [ ] Advanced Search
 - [ ] Download from Search
 - [ ] Modify Attributes from Search

### Upload
 - [ ] Single file upload
 - [ ] Recursive Upload
 - [ ] Compare 
 - [ ] Overwrite
 - [ ] Skip
 - [ ] Filtered by conditions/attributes
 - [ ] Upload from zip-like object
 - [ ] Confirmations for egress
 - [ ] Server-to-Server (aka, buckets)

### Download
 - [ ] Single file download
 - [ ] Recursive download
 - [ ] Filtered by conditions/attributes
 - [ ] Server-to-Server (aka, buckets)
 - [ ] Confirmations for egress

### Update
- [ ] Change file attributes/permissions
- [ ] Recursively change file attributes/permissions
- [ ] Recursively change file attributes/permissions via rules and filters

---
## Ideas:
- Expressive status bar that allows canceling actions
- Reuse and update the StatsQueue from the aCDNBrowser
- Built-in egress cost calculator with programmable warnings for S3 types
- Exportable transfer/actions tracking for records, convenience, sharing, etc.
    i.e., csv, sqlite, xlsx
