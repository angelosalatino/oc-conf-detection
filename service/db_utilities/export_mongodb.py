#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Database Export Utility for COCI MongoDB.
Exports 'events' and 'events_index' collections to a compressed JSON archive (.json.gz) or directory.
Handles BSON serialization (ObjectIds, dates, etc.) safely.
"""

import os
import sys
import argparse
import configparser
import gzip
import json
from pathlib import Path
from datetime import datetime

import pymongo
from bson import json_util


def export_database():
    parser = argparse.ArgumentParser(description="Export COCI MongoDB database collections to a backup file.")
    parser.add_argument("--uri", type=str, help="MongoDB connection URI (overrides config.ini)")
    parser.add_argument("--db", type=str, help="Database name (overrides config.ini)")
    parser.add_argument(
        "--output", "-o", 
        type=str, 
        default=None, 
        help="Output file path (e.g., coci_backup.json or coci_backup.json.gz). Defaults to coci_export_<timestamp>.json.gz"
    )
    parser.add_argument(
        "--uncompressed", 
        action="store_true", 
        help="Export as plain JSON instead of gzip-compressed JSON"
    )
    args = parser.parse_args()

    # Read defaults from config.ini
    config = configparser.ConfigParser()
    config_paths = ['config.ini', '../config.ini', '../../config.ini']
    for cp in config_paths:
        if os.path.exists(cp):
            config.read(cp)
            break

    uri = args.uri or config.get('MONGODB', 'uri', fallback='mongodb://localhost:27017/')
    db_name = args.db or config.get('MONGODB', 'db_name', fallback='coci')

    print(f"Connecting to MongoDB at: {uri}")
    try:
        client = pymongo.MongoClient(uri, serverSelectionTimeoutMS=5000)
        client.server_info()
    except pymongo.errors.ServerSelectionTimeoutError as e:
        print(f"❌ Error: Could not connect to MongoDB server. Details: {e}")
        sys.exit(1)

    db = client[db_name]
    print(f"Connected to database: '{db_name}'")

    # Fetch collections
    events_coll = db["events"]
    events_idx_coll = db["events_index"]

    events_docs = list(events_coll.find({}))
    events_idx_docs = list(events_idx_coll.find({}))

    print(f"Found {len(events_docs)} document(s) in 'events'")
    print(f"Found {len(events_idx_docs)} document(s) in 'events_index'")

    export_payload = {
        "metadata": {
            "database": db_name,
            "exported_at": datetime.utcnow().isoformat() + "Z",
            "events_count": len(events_docs),
            "events_index_count": len(events_idx_docs),
            "version": "1.0"
        },
        "events_index": events_idx_docs,
        "events": events_docs
    }

    # Determine default output file
    if not args.output:
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        ext = ".json" if args.uncompressed else ".json.gz"
        output_path = Path(f"coci_export_{timestamp_str}{ext}")
    else:
        output_path = Path(args.output)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    is_gzip = output_path.suffix == ".gz" or (not args.uncompressed and not output_path.suffix == ".json")

    # If filename ended in .gz or default compression active:
    if is_gzip and not output_path.name.endswith(".gz"):
        output_path = Path(str(output_path) + ".gz")

    print(f"Exporting to: {output_path} (compressed: {is_gzip})...")

    # Serialize using BSON json_util to preserve types cleanly
    json_data = json_util.dumps(export_payload, indent=2 if not is_gzip else None)

    if is_gzip:
        with gzip.open(output_path, "wt", encoding="utf-8") as f:
            f.write(json_data)
    else:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(json_data)

    file_size_kb = output_path.stat().st_size / 1024
    print(f"✅ Export completed successfully! Saved {file_size_kb:.2f} KB to '{output_path}'.")


if __name__ == "__main__":
    export_database()
