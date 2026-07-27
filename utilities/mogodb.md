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

```!python utilities/reset_mongodb.py --uri "mongodb://localhost:27017/" --db "coci" --force```