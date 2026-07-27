# Walkthrough - MongoDB Storage Integration

We have successfully implemented the new MongoDB storage backend, refactored the file storage backend, and integrated them under a dynamic config-driven dispatcher class.

## Changes Made

### 1. Requirements and Dependencies
- Added `pymongo` package to [requirements.txt](file:///Users/aas358/Development/oc-conf-detection/requirements.txt) to enable MongoDB connectivity.

### 2. Configuration Settings
- Appended `[STORAGE]` and `[MONGODB]` sections to [config.ini](file:///Users/aas358/Development/oc-conf-detection/config.ini):
  - `[STORAGE] type`: allows selecting `file` (default) or `mongodb`.
  - `[MONGODB]`: sets connection parameters such as the `uri` and `db_name`.

### 3. Refactored Storage Layer
- Modified [classes/storage.py](file:///Users/aas358/Development/oc-conf-detection/classes/storage.py):
  - Renamed/Refactored old file storage to `StorageToFile` (with `storage_to_file` alias).
  - Created new `StorageToMongo` class (with `storage_to_mongo` alias).
  - Kept `ConferenceStorage` as a dispatcher/factory class that checks `config.ini` to return either `StorageToFile` or `StorageToMongo` dynamically.
  - Designed Table structure for MongoDB:
    - **`events_index` (Table 2)**: maps progressive `index` to unique `event_name` + `year`.
    - **`events` (Table 1)**: stores the full JSON data (`llm-output` and `processed` structures) with `_id` and `index` set to the progressive index, along with a list of processed `filenames` that contributed to it.
  - Implemented merging and duplicate detection:
    - Checks `events_index` for existing record of the same `event_name` and `year`.
    - If found, it fetches the existing document from `events`, merges the organisers list (handling name matching, ORCID/OpenAlex URL checking, and fields updating like `verified`), unions the topics list, merges the enhanced topics by keeping highest similarity, and saves it back under the same progressive ID.
    - If not found, it queries the highest existing index to allocate the next progressive index, inserts it into `events_index`, and saves a new document in `events`.

---

## Verification and Testing

### Automated Unit Tests
We created a unit test script at `scratch/test_mongo_storage.py` and verified all operations:
- Clear the test collections.
- Save a new event (ISWC 2026) -> assert index 1 is created.
- Save another call for papers for the same event and year (ISWC 2026) -> assert it retrieves the existing document by index 1, merges the new organisers and topics correctly, and updates the list of filenames without creating new records.
- Save a different event (ESWC 2026) -> assert a new index 2 is created.

The automated tests ran and completed successfully:
```bash
Connecting to MongoDB...
Saving first CFP (new event)...
First save assertions passed!
Saving second CFP (same event, same year -> merge)...
Second save (merge) assertions passed!
Saving third CFP (different event -> new index)...
Third save (different event) assertions passed!
All MongoDB storage unit tests passed successfully!
```
