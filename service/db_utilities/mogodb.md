to start the server:

```brew services start mongodb/brew/mongodb-community```

Some output:

```
(base) MCL305860:~ aas358$ mongosh --version
2.9.2
(base) MCL305860:~ aas358$ mongod --version
db version v8.3.7
Build Info: {
    "version": "8.3.7",
    "gitVersion": "34eee04f34989abb7a3d91447976f033f4f74af2",
    "modules": [],
    "allocator": "system",
    "environment": {
        "distarch": "arm64",
        "target_arch": "arm64"
    }
}


# Commands

```mongosh```

```show dbs``` - show databases

```use coci``` - use the coci database

```
db.events.find().pretty()```

```
db.events_index.find().pretty()```

## Reset DB

```python service/db_utilities/reset_mongodb.py --uri "mongodb://localhost:27017/" --db "coci" --force```

## Export DB

Export to compressed archive (default: `coci_export_<timestamp>.json.gz`):
```python service/db_utilities/export_mongodb.py```

Export to a specific file:
```python service/db_utilities/export_mongodb.py --output coci_backup.json.gz```

## Import DB

Import from backup file (clean overwrite with `--drop`):
```python service/db_utilities/import_mongodb.py coci_backup.json.gz --drop --force```

Import and merge / update existing records:
```python service/db_utilities/import_mongodb.py coci_backup.json.gz```

## Import Processed CFPs (Folder of JSONs)

Import JSON files from a folder (e.g. `processed_cfps`) discarding any duplicates:
```python service/db_utilities/import_processed_cfps.py --folder processed_cfps```

Test import first without modifying database:
```python service/db_utilities/import_processed_cfps.py --folder processed_cfps --dry-run```