import json
from pathlib import Path

class ConferenceStorage:
    def __init__(self, dest_folder: str):
        self.dest_folder = dest_folder

    def _get_path(self, filename: str) -> Path:
        cut_filename = Path(filename).stem
        return Path(self.dest_folder) / f"{cut_filename}.json"

    def is_processed(self, filename: str) -> bool:
        """Check if the conference file has already been processed."""
        return self._get_path(filename).is_file()

    def save(self, filename: str, conf_dict: dict, llm_output: dict) -> None:
        """Save both the raw LLM output and the fully processed conference data."""
        path = self._get_path(filename)
        data = {
            "llm-output": llm_output,
            "processed": conf_dict
        }
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
                "processed": data
            }
            
        return data
