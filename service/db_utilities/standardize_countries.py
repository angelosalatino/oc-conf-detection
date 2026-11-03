#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Database Country Standardization Utility for COCI.

Standardizes all organiser countries across MongoDB database records
(and optionally processed JSON files) to their full canonical form
(e.g., 'US', 'USA' -> 'United States', 'UK' -> 'United Kingdom').
Supports creating a backup archive before modifying data, and a --dry-run mode.
"""

import os
import sys
import argparse
import configparser
import json
import gzip
from pathlib import Path
from datetime import datetime
from collections import Counter

try:
    import pymongo
    from bson import json_util
    HAS_PYMONGO = True
except ImportError:
    HAS_PYMONGO = False
    json_util = None


_CACHE = {}

def standardize_country_name(raw_name: str) -> str:
    """Standardize a country name or code to its full canonical form."""
    if not raw_name or not str(raw_name).strip():
        return ""
    val = str(raw_name).strip()
    if val.lower() in ["none", "nan", "null"]:
        return ""
    if val in _CACHE:
        return _CACHE[val]

    # Fast mapping for most frequent abbreviations
    fast_map = {
        "us": "United States",
        "usa": "United States",
        "u.s.": "United States",
        "u.s.a.": "United States",
        "uk": "United Kingdom",
        "u.k.": "United Kingdom",
        "gb": "United Kingdom",
        "gbr": "United Kingdom",
        "the netherlands": "Netherlands",
        "nl": "Netherlands",
        "nld": "Netherlands",
        "de": "Germany",
        "deu": "Germany",
        "fr": "France",
        "fra": "France",
        "it": "Italy",
        "ita": "Italy",
        "es": "Spain",
        "esp": "Spain",
        "ch": "Switzerland",
        "che": "Switzerland",
        "at": "Austria",
        "aut": "Austria",
        "cn": "China",
        "chn": "China",
        "jp": "Japan",
        "jpn": "Japan",
        "in": "India",
        "ind": "India",
        "ca": "Canada",
        "can": "Canada",
        "au": "Australia",
        "aus": "Australia",
        "br": "Brazil",
        "bra": "Brazil",
    }
    if val.lower() in fast_map:
        res = fast_map[val.lower()]
        _CACHE[val] = res
        return res

    try:
        import country_converter as coco
        std = coco.convert(names=val, to='name_short', not_found=None)
        if std and str(std).strip() and str(std).lower() != "not found":
            res = str(std).strip()
        else:
            res = val
    except Exception:
        res = val

    _CACHE[val] = res
    return res


def export_backup(db, output_dir: Path) -> Path:
    """Export a timestamped compressed backup before making modifications."""
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = output_dir / f"coci_pre_standardize_backup_{timestamp_str}.json.gz"

    events_docs = list(db["events"].find({}))
    events_idx_docs = list(db["events_index"].find({}))

    export_payload = {
        "metadata": {
            "database": db.name,
            "exported_at": datetime.utcnow().isoformat() + "Z",
            "events_count": len(events_docs),
            "events_index_count": len(events_idx_docs),
            "reason": "Pre-standardization backup"
        },
        "events_index": events_idx_docs,
        "events": events_docs
    }

    json_data = json_util.dumps(export_payload)
    with gzip.open(backup_file, "wt", encoding="utf-8") as f:
        f.write(json_data)

    file_size_kb = backup_file.stat().st_size / 1024
    print(f"📦 Backup created: '{backup_file.name}' ({file_size_kb:.2f} KB)")
    return backup_file


def standardize_organisers_list(organisers_list: list, transform_counter: Counter) -> tuple[list, int]:
    """Standardize country in a list of organiser dictionaries."""
    if not organisers_list or not isinstance(organisers_list, list):
        return organisers_list, 0

    modified_count = 0
    for org in organisers_list:
        if not isinstance(org, dict):
            continue
        old_val = str(org.get("organiser_country", "")).strip()
        if not old_val or old_val.lower() in ["none", "nan", "null"]:
            continue

        new_val = standardize_country_name(old_val)
        if new_val and new_val != old_val:
            org["organiser_country"] = new_val
            transform_counter[(old_val, new_val)] += 1
            modified_count += 1

    return organisers_list, modified_count


def run_standardization():
    parser = argparse.ArgumentParser(
        description="Standardize all organiser countries in MongoDB database (and optionally JSON files) to full form."
    )
    parser.add_argument("--uri", type=str, help="MongoDB connection URI (overrides config.ini)")
    parser.add_argument("--db", type=str, help="Database name (overrides config.ini)")
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Skip automatic database backup before applying modifications"
    )
    parser.add_argument(
        "--folder", "-f",
        type=str,
        default=None,
        help="Optional path to folder of processed JSON files (e.g. 'processed_cfps' or 'service/processed_cfps') to also standardize"
    )
    parser.add_argument(
        "--files-only",
        action="store_true",
        help="Only standardize files in the specified --folder, skipping MongoDB"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without modifying the database or saving files"
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

    print("=" * 65)
    print("🌍 COCI Database Country Standardization Utility")
    print("=" * 65)

    if args.dry_run:
        print("🔍 DRY-RUN MODE: No changes will be saved to MongoDB or disk.\n")

    skip_mongodb = args.files_only or not HAS_PYMONGO
    if not HAS_PYMONGO and not args.files_only:
        print("⚠️ Notice: 'pymongo' not found in current environment. Proceeding in files-only mode.\n")
        skip_mongodb = True

    transform_counter = Counter()
    events_modified = 0
    total_orgs_updated = 0

    if not skip_mongodb:
        # Connect to MongoDB
        print(f"Connecting to MongoDB at: {uri} (Database: '{db_name}')...")
        try:
            client = pymongo.MongoClient(uri, serverSelectionTimeoutMS=5000)
            client.server_info()
        except pymongo.errors.ServerSelectionTimeoutError as e:
            print(f"❌ Error: Could not connect to MongoDB server. Details: {e}")
            sys.exit(1)

        db = client[db_name]
        events_coll = db["events"]
        total_docs = events_coll.count_documents({})
        print(f"✅ Connected to '{db_name}'. Found {total_docs} document(s) in 'events' collection.\n")

        # Perform Backup if requested
        if not args.no_backup and not args.dry_run:
            script_dir = Path(__file__).resolve().parent
            export_backup(db, script_dir)
            print("")

        # Process MongoDB Events
        print(f"Standardizing organiser countries in MongoDB 'events' collection...")
        cursor = events_coll.find({})
        for doc in cursor:
            doc_modified = False
            doc_id = doc.get("_id")
            processed_data = doc.get("processed", {})
            llm_output = doc.get("llm-output", {})

            # 1. Processed Organisers
            if "organisers" in processed_data and isinstance(processed_data["organisers"], list):
                _, mod_p = standardize_organisers_list(processed_data["organisers"], transform_counter)
                if mod_p > 0:
                    doc_modified = True
                    total_orgs_updated += mod_p

            # 2. LLM-output Organisers (keep in sync)
            if isinstance(llm_output, dict) and "organisers" in llm_output and isinstance(llm_output["organisers"], list):
                _, mod_l = standardize_organisers_list(llm_output["organisers"], transform_counter)
                if mod_l > 0:
                    doc_modified = True

            if doc_modified:
                events_modified += 1
                if not args.dry_run:
                    events_coll.update_one(
                        {"_id": doc_id},
                        {"$set": {
                            "processed": processed_data,
                            "llm-output": llm_output
                        }}
                    )

        print(f"✅ MongoDB processing complete:")
        print(f"   • Events updated:     {events_modified} / {total_docs}")
        print(f"   • Organisers updated: {total_orgs_updated}")
    else:
        print("⏩ Skipping MongoDB collection.")

    # Process JSON Folder if specified
    files_modified = 0
    if args.folder:
        folder_path = Path(args.folder)
        if not folder_path.exists():
            for alt in [Path("../../") / args.folder, Path("../") / args.folder]:
                if alt.exists():
                    folder_path = alt
                    break

        if folder_path.is_dir():
            print(f"\nProcessing JSON files in '{folder_path}'...")
            json_files = sorted(list(folder_path.glob("*.json")))
            for jf in json_files:
                try:
                    with open(jf, "r", encoding="utf-8") as f:
                        file_data = json.load(f)

                    file_mod = False
                    p_data = file_data.get("processed", {})
                    l_data = file_data.get("llm-output", {})

                    if "organisers" in p_data and isinstance(p_data["organisers"], list):
                        _, m_p = standardize_organisers_list(p_data["organisers"], transform_counter)
                        if m_p > 0:
                            file_mod = True
                    if isinstance(l_data, dict) and "organisers" in l_data and isinstance(l_data["organisers"], list):
                        _, m_l = standardize_organisers_list(l_data["organisers"], transform_counter)
                        if m_l > 0:
                            file_mod = True

                    if file_mod:
                        files_modified += 1
                        if not args.dry_run:
                            with open(jf, "w", encoding="utf-8") as f:
                                json.dump(file_data, f, indent=4)
                except Exception as e:
                    print(f"⚠️ Could not process file '{jf.name}': {e}")

            print(f"✅ JSON folder processing complete: {files_modified} / {len(json_files)} files updated.")
        else:
            print(f"\n⚠️ Specified folder '{args.folder}' not found. Skipping file updates.")

    # Print Detailed Transformation Breakdown
    print("\n" + "=" * 65)
    print("📊 Country Transformation Summary:")
    print("=" * 65)
    if transform_counter:
        sorted_transforms = sorted(transform_counter.items(), key=lambda x: (-x[1], x[0][0]))
        for (old_c, new_c), count in sorted_transforms:
            print(f"  • {old_c:<18} -> {new_c:<24} ({count:>3} occurrences)")
    else:
        print("  • All organiser country names were already standardized!")

    print("=" * 65)
    if args.dry_run:
        print("💡 Run without '--dry-run' to apply these changes to the database.")
    else:
        print("🎉 Database successfully standardized!")


if __name__ == "__main__":
    run_standardization()
