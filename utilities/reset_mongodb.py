import sys
import argparse
import configparser
import pymongo

def reset_database():
    parser = argparse.ArgumentParser(description="Reset/Clear COCI MongoDB database collections and recreate indexes")
    parser.add_argument("--uri", type=str, help="MongoDB connection URI (overrides config.ini)")
    parser.add_argument("--db", type=str, help="Database name (overrides config.ini)")
    parser.add_argument("--force", action="store_true", help="Force reset without asking for confirmation")
    args = parser.parse_args()

    # Read defaults from config.ini
    config = configparser.ConfigParser()
    config.read('config.ini')
    
    uri = args.uri or config.get('MONGODB', 'uri', fallback='mongodb://localhost:27017/')
    db_name = args.db or config.get('MONGODB', 'db_name', fallback='coci')

    # Confirm action
    if not args.force:
        confirm = input(f"WARNING: This will drop all data in the 'events' and 'events_index' collections in database '{db_name}'. Are you sure? (y/N): ")
        if confirm.lower().strip() not in ['y', 'yes']:
            print("Reset cancelled.")
            sys.exit(0)

    print(f"Connecting to MongoDB at: {uri}")
    try:
        client = pymongo.MongoClient(uri, serverSelectionTimeoutMS=5000)
        client.server_info()
    except pymongo.errors.ServerSelectionTimeoutError as e:
        print(f"Error: Could not connect to MongoDB server. Details: {e}")
        sys.exit(1)

    db = client[db_name]

    print(f"Dropping collection 'events' in '{db_name}'...")
    db["events"].drop()
    
    print(f"Dropping collection 'events_index' in '{db_name}'...")
    db["events_index"].drop()

    # Recreate collections and indexes
    print("Recreating collections and indexes...")
    db["events"].create_index("filenames")
    db["events"].create_index("index", unique=True)
    db["events_index"].create_index("index", unique=True)
    db["events_index"].create_index([
        ("event_name", pymongo.ASCENDING),
        ("year", pymongo.ASCENDING)
    ], unique=True)

    print("\nDatabase reset and initialized successfully!")

if __name__ == "__main__":
    reset_database()
