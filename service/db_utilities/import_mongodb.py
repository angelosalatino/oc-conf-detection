#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Database Import Utility for COCI MongoDB.
Imports 'events' and 'events_index' collections from a backup file (.json or .json.gz).
Rebuilds appropriate indexes and supports drop/merge options.
"""

import os
import sys
import argparse
import configparser
import gzip
from pathlib import Path

import pymongo
from bson import json_util


def import_database():
    parser = argparse.ArgumentParser(description="Import COCI MongoDB database collections from an export file.")
    parser.add_argument("input_file", type=str, help="Path to export file (.json or .json.gz)")
    parser.add_argument("--uri", type=str, help="MongoDB connection URI (overrides config.ini)")
    parser.add_argument("--db", type=str, help="Database name (overrides config.ini)")
    parser.add_argument(
        "--drop", 
        action="store_true", 
        help="Drop existing collections before importing (recommended for clean migration)"
    )
    parser.add_argument(
        "--force", 
        action="store_true", 
        help="Bypass confirmation prompt when --drop is supplied"
    )
    args = parser.parse_args()

    input_path = Path(args.input_file)
    if not input_path.is_file():
        print(f"❌ Error: Input file '{input_path}' not found.")
        sys.exit(1)

    # Read defaults from config.ini
    config = configparser.ConfigParser()
    config_paths = ['config.ini', '../config.ini', '../../config.ini']
    for cp in config_paths:
        if os.path.exists(cp):
            config.read(cp)
            break

    uri = args.uri or config.get('MONGODB', 'uri', fallback='mongodb://localhost:27017/')
    db_name = args.db or config.get('MONGODB', 'db_name', fallback='coci')

    print(f"Reading backup from: {input_path}")
    is_gzip = input_path.suffix == ".gz"

    try:
        if is_gzip:
            with gzip.open(input_path, "rt", encoding="utf-8") as f:
                raw_json = f.read()
        else:
            with open(input_path, "r", encoding="utf-8") as f:
                raw_json = f.read()
                
        data = json_util.loads(raw_json)
    except Exception as e:
        print(f"❌ Failed to parse backup file: {e}")
        sys.exit(1)

    metadata = data.get("metadata", {})
    events_docs = data.get("events", [])
    events_idx_docs = data.get("events_index", [])

    print(f"Backup Metadata:")
    print(f"  • Source Database: {metadata.get('database', 'unknown')}")
    print(f"  • Export Date:     {metadata.get('exported_at', 'unknown')}")
    print(f"  • Events:          {len(events_docs)}")
    print(f"  • Events Index:    {len(events_idx_docs)}")

    print(f"\nConnecting to MongoDB at: {uri}")
    try:
        client = pymongo.MongoClient(uri, serverSelectionTimeoutMS=5000)
        client.server_info()
    except pymongo.errors.ServerSelectionTimeoutError as e:
        print(f"❌ Error: Could not connect to MongoDB server. Details: {e}")
        sys.exit(1)

    db = client[db_name]
    print(f"Target Database: '{db_name}'")

    if args.drop:
        if not args.force:
            confirm = input(f"⚠️  --drop was specified. This will ERASE existing 'events' and 'events_index' collections in '{db_name}'. Continue? (y/N): ")
            if confirm.lower().strip() not in ['y', 'yes']:
                print("Import cancelled.")
                sys.exit(0)

        print(f"Dropping collection 'events'...")
        db["events"].drop()
        print(f"Dropping collection 'events_index'...")
        db["events_index"].drop()

    # 1. Import events_index collection
    idx_coll = db["events_index"]
    if events_idx_docs:
        print(f"Importing {len(events_idx_docs)} records into 'events_index'...")
        for doc in events_idx_docs:
            idx_coll.replace_one({"_id": doc["_id"]}, doc, upsert=True)

    # 2. Import events collection
    events_coll = db["events"]
    if events_docs:
        print(f"Importing {len(events_docs)} records into 'events'...")
        for doc in events_docs:
            events_coll.replace_one({"_id": doc["_id"]}, doc, upsert=True)

    # 3. Ensure proper indexes exist
    print("Ensuring database indexes...")
    events_coll.create_index("filenames")
    events_coll.create_index("index", unique=True)
    idx_coll.create_index("index", unique=True)
    idx_coll.create_index([
        ("event_name", pymongo.ASCENDING),
        ("year", pymongo.ASCENDING)
    ], unique=True)

    print("\n✅ Database import completed successfully!")
    print(f"Total events in '{db_name}': {events_coll.count_documents({})}")
    print(f"Total events_index in '{db_name}': {idx_coll.count_documents({})}")


if __name__ == "__main__":
    import_database()
