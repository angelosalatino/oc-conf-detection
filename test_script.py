import configparser
import json
import argparse
from pathlib import Path
from classes.orchestrator import Orchestrator

def main():
    parser = argparse.ArgumentParser(description="Headless COCI processing")
    parser.add_argument("filepath", type=str, help="Path to the Call for Papers text file")
    args = parser.parse_args()

    config = configparser.ConfigParser()
    config.read('config.ini')

    api_url = config['DEFAULT']['api_url']
    api_key = config['DEFAULT']['api_key']
    referer = config['TEAM']['website']
    title = config['TEAM']['description']

    with open(args.filepath, 'r', encoding='utf-8', errors='replace') as f:
        cfp_text = f.read()

    print(f"Processing {args.filepath}...")
    orchestrator = Orchestrator(api_url, api_key, referer, title)
    conf = orchestrator.process(cfp_text)

    dest_folder = config['FOLDERS']['destination_folder']
    filename = Path(args.filepath).stem
    out_path = Path(dest_folder) / f"{filename}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with open(out_path, 'w') as fw:
        json.dump(conf.to_dict(), fw, indent=4)
        
    print(f"Done. Result saved to {out_path}")

if __name__ == '__main__':
    main()
