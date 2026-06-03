#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Jun 3 2026

Script to generate OpenAlex topic embeddings and construct the FAISS search index.
Ported from utilities/openalex-topics-embeddigns.ipynb.
"""

import os
import sys
import argparse
import pickle
from pathlib import Path
import pandas as pd
import numpy as np

# Set FAISS configuration before importing the library to ensure clean initialization on all platforms
os.environ['FAISS_OPT_LEVEL'] = ''
try:
    import faiss
except ImportError:
    print("Error: The 'faiss' library is not installed. Please install it using 'pip install faiss-cpu' or 'conda install -c pytorch faiss-cpu'.")
    sys.exit(1)

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    print("Error: The 'sentence-transformers' library is not installed. Please install it using 'pip install sentence-transformers'.")
    sys.exit(1)

# Set up paths relative to this script
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent

def parse_args():
    # Detect default excel file name
    excel_candidates = [
        SCRIPT_DIR / "OpenAlex_topic_mapping_table_new.xlsx",
        SCRIPT_DIR / "Copy of OpenAlex_topic_mapping_table_new.xlsx"
    ]
    default_excel = excel_candidates[0]
    for candidate in excel_candidates:
        if candidate.exists():
            default_excel = candidate
            break

    default_output = PROJECT_ROOT / "data_sources" / "openalex.pickle"

    parser = argparse.ArgumentParser(description="Generate OpenAlex topic embeddings and FAISS index.")
    parser.add_argument(
        "--excel", 
        type=str, 
        default=str(default_excel),
        help=f"Path to the topic mapping Excel file (default: {default_excel})"
    )
    parser.add_argument(
        "--output", 
        type=str, 
        default=str(default_output),
        help=f"Path to save the generated pickle file (default: {default_output})"
    )
    return parser.parse_args()

def main():
    args = parse_args()
    excel_path = Path(args.excel)
    output_path = Path(args.output)

    if not excel_path.exists():
        print(f"Error: Excel mapping table file not found at '{excel_path}'")
        sys.exit(1)

    print(f"Loading Excel file from '{excel_path}'...")
    try:
        xl = pd.ExcelFile(excel_path)
    except Exception as e:
        print(f"Error reading Excel file: {e}")
        sys.exit(1)

    sheet_name = "final_topic_field_subfield_tabl"
    if sheet_name not in xl.sheet_names:
        # Fallback to the first sheet if the expected one doesn't exist
        sheet_name = xl.sheet_names[0]
        print(f"Warning: Sheet '{sheet_name}' not found. Using sheet: '{sheet_name}'")

    df = xl.parse(sheet_name)
    print(f"Successfully loaded sheet. Row count: {len(df)}")

    print("Building OpenAlex hierarchical topic structure...")
    attributes = ('topics', 'keywords', 'old_topics', 'broaders', 'narrowers', 'all_broaders', 'level')
    openalex = {attr: {} for attr in attributes}

    for idx, row in df.iterrows():
        # topic
        openalex['topics'][row['new_topic_label']] = row['topic_id']
        openalex['topics'][row['subfield_name']] = row['subfield_id']
        openalex['topics'][row['field_name']] = row['field_id']
        openalex['topics'][row['domain_name']] = row['domain_id']

        # keywords
        t_keywords = [keyword.strip() for keyword in str(row['keywords']).split(';') if keyword.strip()]
        for keyword in t_keywords:
            if keyword not in openalex['keywords']:
                openalex['keywords'][keyword] = []
            openalex['keywords'][keyword].append(row['new_topic_label'])

        # old_topics
        openalex['old_topics'][row['old_topic_label']] = row['topic_id']

        # broaders
        if row['new_topic_label'] not in openalex['broaders']:
            openalex['broaders'][row['new_topic_label']] = []
        openalex['broaders'][row['new_topic_label']].append(row['subfield_name'])
        
        if row['subfield_name'] not in openalex['broaders']:
            openalex['broaders'][row['subfield_name']] = []
        openalex['broaders'][row['subfield_name']].append(row['field_name'])
        
        if row['field_name'] not in openalex['broaders']:
            openalex['broaders'][row['field_name']] = []
        openalex['broaders'][row['field_name']].append(row['domain_name'])
        
        # narrowers
        if row['domain_name'] not in openalex['narrowers']:
            openalex['narrowers'][row['domain_name']] = []
        openalex['narrowers'][row['domain_name']].append(row['field_name'])
        
        if row['field_name'] not in openalex['narrowers']:
            openalex['narrowers'][row['field_name']] = []
        openalex['narrowers'][row['field_name']].append(row['subfield_name'])
        
        if row['subfield_name'] not in openalex['narrowers']:
            openalex['narrowers'][row['subfield_name']] = []
        openalex['narrowers'][row['subfield_name']].append(row['new_topic_label'])
        
        # all_broaders
        for keyword in t_keywords:
            if keyword not in openalex['all_broaders']:
                openalex['all_broaders'][keyword] = []
            openalex['all_broaders'][keyword] += [row['new_topic_label'], row['subfield_name'], row['field_name'], row['domain_name']]
        
        if row['old_topic_label'] not in openalex['all_broaders']:
            openalex['all_broaders'][row['old_topic_label']] = [row['subfield_name'], row['field_name'], row['domain_name']]
        
        if row['new_topic_label'] not in openalex['all_broaders']:
            openalex['all_broaders'][row['new_topic_label']] = [row['subfield_name'], row['field_name'], row['domain_name']]
        
        if row['subfield_name'] not in openalex['all_broaders']:
            openalex['all_broaders'][row['subfield_name']] = [row['field_name'], row['domain_name']]
        
        if row['field_name'] not in openalex['all_broaders']:
            openalex['all_broaders'][row['field_name']] = [row['domain_name']]
        
        # level
        openalex['level'][row['new_topic_label']] = 3
        openalex['level'][row['subfield_name']] = 2
        openalex['level'][row['field_name']] = 1
        openalex['level'][row['domain_name']] = 0

    # clean broaders, narrowers, and all_broaders by removing duplicates
    print("De-duplicating broaders, narrowers, and all_broaders...")
    for k, v in openalex['broaders'].items():
        openalex['broaders'][k] = list(set(v))
    for k, v in openalex['narrowers'].items():
        openalex['narrowers'][k] = list(set(v))
    for k, v in openalex['all_broaders'].items():
        openalex['all_broaders'][k] = list(set(v))

    # Extracting the embeddings
    print("Collecting unique concepts and keywords...")
    unique_concepts = set(df['new_topic_label']).union(
        set(df['subfield_name'])
    ).union(
        set(df['field_name'])
    ).union(
        set(df['domain_name'])
    ).union(
        set(df['old_topic_label'])
    )
    
    print(f"Base concepts count: {len(unique_concepts)}")

    list_of_keywords = []
    for idx, row in df.iterrows():
        list_of_keywords += [keyword.strip() for keyword in str(row['keywords']).split(';') if keyword.strip()]
    
    print(f"Total keyword occurrences: {len(list_of_keywords)}")
    unique_keywords = set(list_of_keywords)
    print(f"Unique keywords count: {len(unique_keywords)}")

    unique_concepts = unique_concepts.union(unique_keywords)
    print(f"Total unique concepts to encode: {len(unique_concepts)}")

    print("Loading pretrained SentenceTransformer model ('all-MiniLM-L6-v2')...")
    model = SentenceTransformer("all-MiniLM-L6-v2")

    sentences = list(unique_concepts)
    print("Calculating embeddings (this may take a few minutes)...")
    embeddings = model.encode(sentences, show_progress_bar=True)
    print(f"Generated embeddings shape: {embeddings.shape}")
    vector_size = embeddings.shape[1]

    print("Building FAISS Index...")
    index = faiss.IndexFlatL2(vector_size)
    print(f"FAISS Index is_trained: {index.is_trained}")

    print("Adding embeddings to the FAISS index...")
    index.add(embeddings)
    print(f"FAISS index total vectors: {index.ntotal}")

    print(f"Saving compiled structure and index to '{output_path}'...")
    to_save = {
        "sentences": sentences,
        "index": index,
        "structure": openalex
    }

    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'wb') as handle:
        pickle.dump(to_save, handle, protocol=pickle.HIGHEST_PROTOCOL)

    print("Generation complete! All structures and index are ready for use.")

if __name__ == '__main__':
    main()
