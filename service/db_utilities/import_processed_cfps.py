#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Import Processed CFPs into MongoDB.

Imports all processed JSON conference files from a folder into MongoDB.
If a conference already exists in MongoDB (matched by event_name and year,
or by filename stem), it will discard/skip the duplicate to avoid modifying or overwriting existing entries.
"""

import os
import sys
import argparse
import configparser
import json
from pathlib import Path
from datetime import datetime

import pymongo


def import_processed_cfps():
    parser = argparse.ArgumentParser(description="Import processed CFP JSON files into MongoDB.")
    parser.add_argument(
        "--folder", "-f",
        type=str,
        default="processed_cfps",
        help="Path to the folder containing processed JSON files (default: 'processed_cfps')"
    )
    parser.add_argument("--uri", type=str, help="MongoDB connection URI (overrides config.ini)")
    parser.add_argument("--db", type=str, help="Database name (overrides config.ini)")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate the import and report duplicates without writing to MongoDB"
    )
    args = parser.parse_args()

    # Locate config.ini
    config = configparser.ConfigParser()
    config_paths = ['config.ini', '../config.ini', '../../config.ini']
    for cp in config_paths:
        if os.path.exists(cp):
            config.read(cp)
            break

    uri = args.uri or config.get('MONGODB', 'uri', fallback='mongodb://localhost:27017/')
    db_name = args.db or config.get('MONGODB', 'db_name', fallback='coci')

    # Resolve folder path
    folder_path = Path(args.folder)
    if not folder_path.exists():
        # Check relative to repo root if run from service/db_utilities
        alt_path = Path("../../") / args.folder
        if alt_path.exists():
            folder_path = alt_path
        else:
            alt_path2 = Path("../") / args.folder
            if alt_path2.exists():
                folder_path = alt_path2

    if not folder_path.is_dir():
        print(f"❌ Error: Folder '{args.folder}' does not exist or is not a directory.")
        sys.exit(1)

    json_files = sorted(list(folder_path.glob("*.json")))
    if not json_files:
        print(f"ℹ️ No JSON files found in '{folder_path}'.")
        sys.exit(0)

    print(f"📂 Found {len(json_files)} JSON file(s) in '{folder_path}'")
    print(f"🔌 Connecting to MongoDB at: {uri} (database: '{db_name}')...")

    try:
        client = pymongo.MongoClient(uri, serverSelectionTimeoutMS=5000)
        client.server_info()
    except pymongo.errors.ServerSelectionTimeoutError as e:
        print(f"❌ Error: Could not connect to MongoDB server. Details: {e}")
        sys.exit(1)

    db = client[db_name]
    events_coll = db["events"]
    events_idx_coll = db["events_index"]

    # Ensure indexes exist
    events_coll.create_index("filenames")
    events_coll.create_index("index", unique=True)
    events_idx_coll.create_index("index", unique=True)
    events_idx_coll.create_index([
        ("event_name", pymongo.ASCENDING),
        ("year", pymongo.ASCENDING)
    ], unique=True)

    imported_count = 0
    discarded_duplicates = 0
    invalid_count = 0

    from datetime import timezone
    now_iso = datetime.now(timezone.utc).isoformat()

    print("\nStarting import with duplicate detection (duplicates will be discarded)...\n")

    for file_path in json_files:
        filename_stem = file_path.stem

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print(f"⚠️  [INVALID] Could not parse '{file_path.name}': {e}")
            invalid_count += 1
            continue

        # Extract conference details
        llm_output = data.get("llm-output", {})
        processed = data.get("processed", {})
        cfp_text = data.get("cfp_text", "")

        # Fallback for old schema where processed may be at top-level
        if not processed and "event_name" in data:
            processed = data
            llm_output = data

        event_name = str(processed.get("event_name") or llm_output.get("event_name", "")).strip()
        conference_series = str(processed.get("conference_series") or llm_output.get("conference_series", "")).strip()
        year = str(processed.get("year") or llm_output.get("year", "")).strip()

        if not event_name and not processed:
            print(f"⚠️  [SKIPPED] '{file_path.name}': No event_name or processed content found.")
            invalid_count += 1
            continue

        # Check for duplicates:
        # 1. Match by (event_name, year) in events_index
        duplicate_reason = None
        if event_name and year:
            existing_by_name = events_idx_coll.find_one({
                "event_name": event_name,
                "year": year
            })
            if existing_by_name:
                duplicate_reason = f"Event '{event_name}' ({year}) already exists with index {existing_by_name.get('index')}"

        # 2. Match by filename stem in events
        if not duplicate_reason:
            existing_by_filename = events_coll.find_one({
                "filenames": filename_stem
            })
            if existing_by_filename:
                duplicate_reason = f"Filename stem '{filename_stem}' already indexed in event {existing_by_filename.get('_id')}"

        if duplicate_reason:
            print(f"⏩ [DISCARDED DUPLICATE] '{file_path.name}': {duplicate_reason}")
            discarded_duplicates += 1
            continue

        # If dry run, skip actual insertion
        if args.dry_run:
            print(f"🔎 [WOULD IMPORT] '{file_path.name}' -> Event: '{event_name}', Year: '{year}'")
            imported_count += 1
            continue

        # Allocate progressive index
        max_doc = events_idx_coll.find_one(sort=[("index", -1)])
        new_idx = (max_doc["index"] + 1) if max_doc else 1

        # Insert into events_index (Table 2)
        try:
            events_idx_coll.insert_one({
                "index": new_idx,
                "event_name": event_name,
                "conference_series": conference_series,
                "year": year
            })
        except pymongo.errors.DuplicateKeyError:
            print(f"⏩ [DISCARDED DUPLICATE] Concurrent duplicate on index/event_name for '{file_path.name}'")
            discarded_duplicates += 1
            continue

        # Insert into events (Table 1)
        created_at = data.get("created_at") or now_iso
        processed_at = data.get("processed_at") or now_iso

        events_coll.insert_one({
            "_id": new_idx,
            "index": new_idx,
            "filenames": [filename_stem],
            "cfps": [cfp_text if cfp_text else ""],
            "llm-output": llm_output,
            "processed": processed,
            "created_at": created_at,
            "processed_at": processed_at
        })

        print(f"✅ [IMPORTED] '{file_path.name}' -> Index: {new_idx} ('{event_name}', {year})")
        imported_count += 1

    print("\n" + "="*50)
    print("📊 Import Summary:")
    print(f"  • Total files evaluated:   {len(json_files)}")
    print(f"  • Successfully imported:   {imported_count}")
    print(f"  • Discarded duplicates:    {discarded_duplicates}")
    if invalid_count > 0:
        print(f"  • Invalid/Empty files:     {invalid_count}")
    if args.dry_run:
        print("  • Note: Dry-run mode was ON. No database changes were applied.")
    print("="*50)


if __name__ == "__main__":
    import_processed_cfps()
