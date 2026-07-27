import sys
import argparse
import configparser
import pymongo

def initialize_database():
    parser = argparse.ArgumentParser(description="Initialize MongoDB Database for COCI")
    parser.add_argument("--uri", type=str, help="MongoDB connection URI (overrides config.ini)")
    parser.add_argument("--db", type=str, help="Database name (overrides config.ini)")
    args = parser.parse_args()

    # Read defaults from config.ini
    config = configparser.ConfigParser()
    config.read('config.ini')
    
    uri = args.uri or config.get('MONGODB', 'uri', fallback='mongodb://localhost:27017/')
    db_name = args.db or config.get('MONGODB', 'db_name', fallback='coci')

    print(f"Connecting to MongoDB at: {uri}")
    try:
        client = pymongo.MongoClient(uri, serverSelectionTimeoutMS=5000)
        # Trigger connection check
        client.server_info()
    except pymongo.errors.ServerSelectionTimeoutError as e:
        print(f"Error: Could not connect to MongoDB server. Details: {e}")
        sys.exit(1)

    db = client[db_name]
    print(f"Using database: '{db_name}'")

    # 1. Setup events collection (Table 1)
    print("Setting up 'events' collection...")
    events_coll = db["events"]
    
    # Create index on filenames for fast checks (is_processed) and loading
    print("Creating index on 'filenames' in 'events' collection...")
    events_coll.create_index("filenames")
    
    # Create unique index on 'index' field (in addition to default _id unique index)
    print("Creating unique index on 'index' in 'events' collection...")
    events_coll.create_index("index", unique=True)

    # 2. Setup events_index collection (Table 2)
    print("Setting up 'events_index' collection...")
    idx_coll = db["events_index"]
    
    # Create unique index on index
    print("Creating unique index on 'index' in 'events_index' collection...")
    idx_coll.create_index("index", unique=True)
    
    # Create unique compound index on event_name + year to guarantee uniqueness and enable fast queries
    print("Creating unique compound index on 'event_name' and 'year' in 'events_index' collection...")
    idx_coll.create_index([
        ("event_name", pymongo.ASCENDING),
        ("year", pymongo.ASCENDING)
    ], unique=True)

    print("\nDatabase initialization completed successfully!")
    print("MongoDB tables/collections and indexes are ready.")

if __name__ == "__main__":
    initialize_database()
