import json
import configparser
from pathlib import Path
import pymongo

class StorageToFile:
    def __init__(self, dest_folder: str):
        self.dest_folder = dest_folder

    def _get_path(self, filename: str) -> Path:
        cut_filename = Path(filename).stem
        return Path(self.dest_folder) / f"{cut_filename}.json"

    def is_processed(self, filename: str) -> bool:
        """Check if the conference file has already been processed."""
        return self._get_path(filename).is_file()

    def save(self, filename: str, conf_dict: dict, llm_output: dict, cfp_text: str = None) -> None:
        """Save both the raw LLM output and the fully processed conference data, preserving/saving cfp_text."""
        path = self._get_path(filename)
        
        existing_cfp = None
        if path.is_file():
            try:
                with open(path, 'r') as f:
                    old_data = json.load(f)
                existing_cfp = old_data.get("cfp_text")
            except Exception:
                pass
        
        final_cfp = cfp_text if cfp_text is not None else existing_cfp
        
        data = {
            "llm-output": llm_output,
            "processed": conf_dict
        }
        if final_cfp is not None:
            data["cfp_text"] = final_cfp
            
        with open(path, 'w') as f:
            json.dump(data, f, indent=4)

    def load(self, filename: str) -> dict:
        """
        Load the saved data. Provides backward compatibility for older JSON
        files that didn't have the "llm-output" and "processed" keys.
        """
        path = self._get_path(filename)
        with open(path, 'r') as f:
            data = json.load(f)
        
        # Backward compatibility for old JSON schema
        if "processed" not in data and "event_name" in data:
            return {
                "llm-output": data,
                "processed": data,
                "cfp_text": data.get("cfp_text", "")
            }
            
        return {
            "llm-output": data.get("llm-output", {}),
            "processed": data.get("processed", {}),
            "cfp_text": data.get("cfp_text", "")
        }


def merge_dict(existing_dict, new_dict):
    if not existing_dict:
        return new_dict or {}
    if not new_dict:
        return existing_dict or {}
    merged = dict(existing_dict)
    for k, v in new_dict.items():
        if not merged.get(k) and v:
            merged[k] = v
    return merged


def merge_organisers(existing_orgs, new_orgs):
    merged = list(existing_orgs)
    for new_org in new_orgs:
        name = new_org.get("organiser_name", "").strip()
        orcid = new_org.get("orcid", "")
        openalex_page = new_org.get("openalex_page", "")
        
        # Find if there is an existing matching organiser
        match_idx = -1
        for idx, ext_org in enumerate(merged):
            ext_name = ext_org.get("organiser_name", "").strip()
            ext_orcid = ext_org.get("orcid", "")
            ext_openalex = ext_org.get("openalex_page", "")
            
            # Check for match
            if orcid and ext_orcid and orcid == ext_orcid:
                match_idx = idx
                break
            if openalex_page and ext_openalex and openalex_page == ext_openalex:
                match_idx = idx
                break
            if name.lower() == ext_name.lower() and name:
                match_idx = idx
                break
        
        if match_idx >= 0:
            # Merge fields of the organiser
            ext_org = merged[match_idx]
            for key, val in new_org.items():
                if not ext_org.get(key) and val:
                    ext_org[key] = val
                elif key == "verified" and val is True:
                    ext_org["verified"] = True
        else:
            merged.append(new_org)
    return merged


def merge_topics(existing_topics, new_topics):
    merged = list(existing_topics)
    existing_set = {t.lower().strip() for t in existing_topics if isinstance(t, str)}
    for t in new_topics:
        if not isinstance(t, str):
            continue
        t_clean = t.strip()
        if t_clean.lower() not in existing_set:
            merged.append(t)
            existing_set.add(t_clean.lower())
    return merged


def merge_enhanced_topics(existing_enhanced, new_enhanced):
    merged = dict(existing_enhanced)
    for topic, new_matches in new_enhanced.items():
        if topic not in merged:
            merged[topic] = new_matches
        else:
            # Merge the lists of topic matches (dicts)
            existing_matches = merged[topic]
            match_map = {m["topic"].lower(): m for m in existing_matches if isinstance(m, dict) and "topic" in m}
            for m in new_matches:
                if not isinstance(m, dict) or "topic" not in m:
                    continue
                topic_name_lower = m["topic"].lower()
                if topic_name_lower in match_map:
                    # Keep the one with higher similarity
                    existing_sim = match_map[topic_name_lower].get("similarity", 0)
                    new_sim = m.get("similarity", 0)
                    if new_sim > existing_sim:
                        match_map[topic_name_lower]["similarity"] = new_sim
                else:
                    existing_matches.append(m)
    return merged


def merge_event_data(existing_data: dict, new_data: dict) -> dict:
    merged = dict(existing_data)
    
    # Merge basic fields
    for key in ["event_name", "event_acronym", "conference_series", "colocated_with", "year", "location"]:
        ext_val = merged.get(key)
        new_val = new_data.get(key)
        if not ext_val and new_val:
            merged[key] = new_val
            
    for key in ["DBLP", "AIDA", "ConfIDent"]:
        merged[key] = merge_dict(merged.get(key), new_data.get(key))
        
    # Merge organisers
    merged["organisers"] = merge_organisers(merged.get("organisers", []), new_data.get("organisers", []))
    
    # Merge topics
    merged["topics"] = merge_topics(merged.get("topics", []), new_data.get("topics", []))
    
    # Merge enhanced_topics
    merged["enhanced_topics"] = merge_enhanced_topics(merged.get("enhanced_topics", {}), new_data.get("enhanced_topics", {}))
    
    # For any other fields not explicitly handled, if existing doesn't have it, copy from new
    for k, v in new_data.items():
        if k not in merged:
            merged[k] = v
            
    return merged


class StorageToMongo:
    def __init__(self, uri: str, db_name: str):
        self.uri = uri
        self.db_name = db_name
        self.client = pymongo.MongoClient(uri)
        self.db = self.client[db_name]
        self.events = self.db["events"]
        self.events_index = self.db["events_index"]

    def is_processed(self, filename: str) -> bool:
        """Check if the conference file has already been processed."""
        stem = Path(filename).stem
        return self.events.find_one({"filenames": stem}) is not None

    def load(self, filename: str) -> dict:
        """Load the saved data from the database."""
        stem = Path(filename).stem
        doc = self.events.find_one({"filenames": stem})
        if not doc:
            raise FileNotFoundError(f"No database record found for filename {filename}")
        
        filenames = doc.get("filenames", [])
        cfps = doc.get("cfps", [])
        
        cfp_text = ""
        try:
            idx = filenames.index(stem)
            if idx < len(cfps):
                cfp_text = cfps[idx]
        except ValueError:
            if cfps:
                cfp_text = cfps[0]
        
        # Construct standard dict with "llm-output", "processed" and "cfp_text"
        return {
            "llm-output": doc.get("llm-output", {}),
            "processed": doc.get("processed", {}),
            "cfp_text": cfp_text
        }

    def save(self, filename: str, conf_dict: dict, llm_output: dict, cfp_text: str = None) -> None:
        """Save both the raw LLM output and the fully processed conference data to MongoDB."""
        stem = Path(filename).stem
        
        # Extract event name, conference series, and year
        event_name = conf_dict.get("event_name") or llm_output.get("event_name", "")
        conference_series = conf_dict.get("conference_series") or llm_output.get("conference_series", "")
        year = conf_dict.get("year") or llm_output.get("year", "")
        
        event_name_str = str(event_name).strip()
        conference_series_str = str(conference_series).strip()
        year_str = str(year).strip()
        
        # Quick lookup in events_index (Table 2)
        existing_idx_doc = self.events_index.find_one({
            "event_name": event_name_str,
            "year": year_str
        })
        
        if existing_idx_doc:
            idx = existing_idx_doc["index"]
            
            # Update conference_series in events_index if missing but now available
            if not existing_idx_doc.get("conference_series") and conference_series_str:
                self.events_index.update_one(
                    {"_id": existing_idx_doc["_id"]},
                    {"$set": {"conference_series": conference_series_str}}
                )
            
            # Retrieve from events (Table 1)
            existing_event = self.events.find_one({"_id": idx})
            
            if existing_event:
                # Merge the information
                merged_processed = merge_event_data(existing_event.get("processed", {}), conf_dict)
                merged_llm_output = merge_event_data(existing_event.get("llm-output", {}), llm_output)
                filenames = existing_event.get("filenames", [])
                
                # Fetch existing CFPs list and ensure length aligns
                cfps = existing_event.get("cfps", [])
                if not isinstance(cfps, list):
                    # Migration fallback if old structure was a dict
                    cfps = [cfps.get(f, "") for f in filenames] if isinstance(cfps, dict) else []
                
                while len(cfps) < len(filenames):
                    cfps.append("")
                
                if stem not in filenames:
                    filenames.append(stem)
                    cfps.append(cfp_text if cfp_text is not None else "")
                else:
                    stem_idx = filenames.index(stem)
                    if cfp_text is not None:
                        cfps[stem_idx] = cfp_text
                
                self.events.replace_one(
                    {"_id": idx},
                    {
                        "_id": idx,
                        "index": idx,
                        "filenames": filenames,
                        "cfps": cfps,
                        "llm-output": merged_llm_output,
                        "processed": merged_processed
                    }
                )
            else:
                # Fallback if events_index doc exists but events doc is missing
                cfps = [cfp_text if cfp_text is not None else ""]
                self.events.insert_one({
                    "_id": idx,
                    "index": idx,
                    "filenames": [stem],
                    "cfps": cfps,
                    "llm-output": llm_output,
                    "processed": conf_dict
                })
        else:
            # Generate new progressive index
            max_doc = self.events_index.find_one(sort=[("index", -1)])
            new_idx = (max_doc["index"] + 1) if max_doc else 1
            
            # Insert into events_index
            self.events_index.insert_one({
                "index": new_idx,
                "event_name": event_name_str,
                "conference_series": conference_series_str,
                "year": year_str
            })
            
            cfps = [cfp_text if cfp_text is not None else ""]
            
            # Insert into events
            self.events.insert_one({
                "_id": new_idx,
                "index": new_idx,
                "filenames": [stem],
                "cfps": cfps,
                "llm-output": llm_output,
                "processed": conf_dict
            })


class StorageToBoth:
    def __init__(self, dest_folder: str, uri: str, db_name: str):
        self.file_storage = StorageToFile(dest_folder)
        self.mongo_storage = StorageToMongo(uri, db_name)

    def is_processed(self, filename: str) -> bool:
        """Check if the conference file has already been processed in either file storage or MongoDB."""
        return self.file_storage.is_processed(filename) or self.mongo_storage.is_processed(filename)

    def load(self, filename: str) -> dict:
        """Load the saved data. Prefers file storage, falls back to MongoDB."""
        try:
            return self.file_storage.load(filename)
        except Exception:
            return self.mongo_storage.load(filename)

    def save(self, filename: str, conf_dict: dict, llm_output: dict, cfp_text: str = None) -> None:
        """Save both the raw LLM output and the fully processed conference data to both file storage and MongoDB."""
        self.file_storage.save(filename, conf_dict, llm_output, cfp_text)
        self.mongo_storage.save(filename, conf_dict, llm_output, cfp_text)


# Aliases as requested
storage_to_file = StorageToFile
storage_to_mongo = StorageToMongo
storage_to_both = StorageToBoth


class ConferenceStorage:
    def __new__(cls, dest_folder: str):
        config = configparser.ConfigParser()
        config.read('config.ini')
        storage_type = config.get('STORAGE', 'type', fallback='file')
        # Clean inline comments and whitespace
        storage_type = storage_type.split('#')[0].split(';')[0].strip()
        
        uri = config.get('MONGODB', 'uri', fallback='mongodb://localhost:27017/')
        db_name = config.get('MONGODB', 'db_name', fallback='coci')
        
        if storage_type == 'mongodb':
            return StorageToMongo(uri, db_name)
        elif storage_type == 'both':
            return StorageToBoth(dest_folder, uri, db_name)
        else:
            return StorageToFile(dest_folder)

