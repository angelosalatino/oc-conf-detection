#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Aug 18 09:05:26 2025

@author: aas358
"""
import streamlit as st
import configparser
from openai import OpenAI
from pyalex import config
from pyalex import Authors, Institutions
from pathlib import Path
from sentence_transformers import SentenceTransformer
import faiss  
import pickle
import urllib.parse
import json
from rapidfuzz.distance import Levenshtein
from rapidfuzz import fuzz
import json



def create_destination_path(filename:str)->str:
    """
    Constructs the destination file path for the processed conference data.

    Args:
        filename (str): The name of the uploaded file.

    Returns:
        str: The full path where the JSON output will be saved.
    """
    # Extract the filename without extension
    cut_filename = Path(filename).stem
    # Construct the path using the folder defined in the configuration
    return f"{st.session_state['config']['FOLDERS']['destination_folder']}/{cut_filename}.json"

def check_if_file_was_previously_processed(filename:str)->bool:
    """
    Checks if a file has already been processed by looking for its output JSON.

    Args:
        filename (str): The name of the uploaded file.

    Returns:
        bool: True if the file exists, False otherwise.
    """
    complete_path = create_destination_path(filename)
    my_file = Path(complete_path)
    # Check if the file exists in the filesystem
    if my_file.is_file():
        return True
    else:
        return False


def read_config_file():
    """Reads the configuration file 'config.ini' and stores it in the Streamlit session state."""
    if 'config' not in st.session_state:
        st.session_state['config'] = configparser.ConfigParser()
        st.session_state['config'].read('config.ini')
    

def connect_to_OpenRouter():
    """
    Establishes a connection to the OpenRouter API (or compatible OpenAI interface).

    Returns:
        OpenAI: An instance of the OpenAI client configured with the API key and URL.
    """
    api_url = st.session_state['config']['DEFAULT']['api_url']
    api_key = st.session_state['config']['DEFAULT']['api_key']
    
    # Check if API key is present
    if len(api_key) == 0:
        print("API Key missing!")
        
    # Initialize the OpenAI client
    client = OpenAI(
      base_url=api_url,
      api_key=api_key,
    )
    return client

def prepare_prompt(call_for_papers:str)->str:
    """
    Creates the prompt string to be sent to the LLM.

    Args:
        call_for_papers (str): The raw text of the Call for Papers.

    Returns:
        str: The formatted prompt string.
    """
    text_prompt = f"""In this prompt, you will receive a Call for Papers of a scientific event. Your task is to parse it, and identify some crucial elements:

                - the event name and its acronym;
                - the location of the event
                - the organisers of the event
                
                <call_for_papers>
                {call_for_papers}
                </call_for_papers>"""
    return text_prompt
                
def run_model(client:OpenAI, call_for_papers:str)->dict:
    """
    Sends the Call for Papers to the LLM and retrieves the structured information.

    Args:
        client (OpenAI): The OpenAI client instance.
        call_for_papers (str): The raw text of the Call for Papers.

    Returns:
        dict: A dictionary containing the structured event information extracted by the model.
    """
                            
    text_prompt = prepare_prompt(call_for_papers=call_for_papers)
                
    true = True
    false = False
    # Set headers for OpenRouter to identify the application
    extra_headers={
        "HTTP-Referer": st.session_state['config']['TEAM']['website'], # Optional. Site URL for rankings on openrouter.ai.
        "X-Title": st.session_state['config']['TEAM']['description'], # Optional. Site title for rankings on openrouter.ai.
        }
    model="openai/gpt-4o"
    messages= [
        { "role": "user", "content": text_prompt }
        ]
    # Define the JSON schema for the expected response
    response_format={
        "type": "json_schema",
        "json_schema": {
          "name": "organising_committe_of_conference",
          "strict": true,
          "schema": {
            "type": "object",
            "properties": {
              "event_name": {
                "type": "string",
                "description": "Name of the workshop or conference. This identifies the extended name of the event."
              },
              "conference_series": {
                "type": "string",
                "description": "This refers to the name of a conference series, which is a collection of events that happen on a regular basis. It's usually similar to the event_name property, but without the edition number or the year. Also it does not contain the event_acronym."
              },
              "event_acronym": {
                "type": "string",
                "description": "Acronym of the workshop or conference. This identifies the acronym name of the event."
              },
              "colocated_with": {
                "type": "string",
                "description": "If the name of the event is co-located with another big event. Otherwise if empty."
              },
              "location": {
                "type": "string",
                "description": "City or location name"
              },
              "organisers": {
                "type": "array",
                "items": {
                        "type": "object",
                        "properties": {
                            "organiser_name": {
                                "type": "string",
                                "description": "The organiser name."
                            },
                            "organiser_affiliation": {
                                "type": "string",
                                "description": "The institution (affiliation) of the organiser. This can be either a university or a company."
                            },
                            "organiser_country": {
                                "type": "string",
                                "description": "The institution country of the organiser. This information is not always available."
                            },
                            "track_name": {
                                "type": "string",
                                "description": "This identifies the main track in which the organiser is involved. A conference may have several tracks, whereas a workshop may have one single track. As default value you shall use 'main' if there are no tracks."
                            }
                        },
                    "required": ["organiser_name", "organiser_affiliation", "organiser_country", "track_name"],
                    "additionalProperties": false
                    },
                "description": "Identifies the name, affiliation (ideally including country) of the conference organisers and the name of the track they organise."
              }
            },
            "required": ["event_name", "event_acronym", "conference_series", "colocated_with", "location", "organisers"],
            "additionalProperties": false
          }
        }
        }
    
    # Call the API
    completion = client.chat.completions.create(extra_headers=extra_headers, 
                                            model=model, 
                                            messages=messages, 
                                            response_format=response_format)
    # Parse the JSON response
    result = json.loads(completion.choices[0].message.content)
    
    
    # Post-processing: clean the track name, as it is harder to do this via LLM reliably
    tracks = set()
    for organiser in result["organisers"]:
        tracks.add(organiser["track_name"])
    
    # If multiple tracks are detected, normalize 'main' track to 'Other' if necessary
    multi_track = True if len(tracks) > 1 else False
    if multi_track:
        for organiser in result["organisers"]:
            if organiser["track_name"].lower() == "main":
                print("Changed")
                organiser["track_name"] = "Other"
    
    
    return result


def get_authors_info_from_openalex(organisers:list)->list:
    """
    Enriches the organiser information by querying OpenAlex.
    
    This function attempts to find the author in OpenAlex to retrieve their
    OpenAlex ID, ORCID, and ROR (Research Organization Registry) ID for their affiliation.
    
    It uses a two-step approach:
    1. Search by affiliation (Institution) + Author Name.
    2. If that fails, search by Author Name and disambiguate using string similarity.
    

    Parameters
    ----------
    organisers : list
        A list of dictionaries, each representing an organiser.

    Returns
    -------
    list
        The updated list of organisers with OpenAlex information.

    """

    ### First we attempt to located the organiser by finding their affiliation, and filtering them by affiliation
    ### Second attempt is made when the affiliation is not clear.
    
    
    DEBUG = True
    for organiser in organisers:
        
        # Initialize fields
        organiser["openalex_name"] = ""
        organiser["openalex_page"] = ""
        organiser["orcid"] = ""
        organiser["affiliation_ror"] = ""
        organiser["verified"] = False
        
        print("HERE")
        print(organisers)
        
        find_author_with_less_info = False
        orga = {}
        
        # Attempt 1: Search using Institution
        if len(organiser["organiser_affiliation"]) > 0:
            # Search for the institution and then filtering
            insts = Institutions().search(organiser["organiser_affiliation"]).get()
            if len(insts) > 0:
                inst_id = insts[0]["id"].replace("https://openalex.org/", "")
        
                if "ror" in insts[0]["ids"]:
                    organiser["affiliation_ror"] = insts[0]["ids"]["ror"]
                
                # Search for the author within the institution
                auths = Authors().search(organiser["organiser_name"]).filter(affiliations={"institution":{"id": inst_id}}).get()
                if len(auths) > 0:        
                    if DEBUG: print(f"{len(auths)} search results found for the author")
                    orga = auths[0]
                else:
                    find_author_with_less_info = True
                    if DEBUG: print(f"For {organiser['organiser_name']} I could not find a record")
                
                    
            else:
                find_author_with_less_info = True
                if DEBUG: print(f"For {organiser['organiser_name']} I could not find a record of their institution")
        else:
            find_author_with_less_info = True
            if DEBUG: print(f"For {organiser['organiser_name']} there is no affiliation")
    
        # Attempt 2: Search for authors without institution info (or if Attempt 1 failed)
        if find_author_with_less_info:
            auths = Authors().search(organiser['organiser_name']).get()
            if len(auths) == 1:
                orga = auths[0]
            elif len(auths) == 0:
                if DEBUG: print(f"For {organiser['organiser_name']} I could not find a record, AGAIN")
            else:
                if DEBUG: print(f"Found multiple records for {organiser['organiser_name']}")
                # Sort by works count to prioritize more prolific authors (heuristic)
                new_auths = sorted(auths, key=lambda item: item['works_count'], reverse=True)
    
                # Match the author with the most similar name (handling variations)
                max_similarity = 0
                final_position = -1
                for author_position, new_auth in enumerate(new_auths):
                    all_alternative_names = new_auth["display_name_alternatives"]
                    for alternative_name in all_alternative_names:
                        author_similarity = Levenshtein.normalized_similarity(alternative_name,organiser['organiser_name'])
                        if author_similarity > max_similarity:
                            if DEBUG: print(f"{alternative_name}; {author_position}; {author_similarity}")
                            max_similarity = author_similarity
                            final_position = author_position
    
                orga = new_auths[final_position]
    
        # If an author record was found, populate the organiser dictionary
        if len(orga) > 0:
            organiser["openalex_name"] = orga["display_name"]
            organiser["openalex_page"] = orga["id"]
            organiser["orcid"] = orga["orcid"]
            
            # Try to recover ROR if it wasn't found earlier but we have the author
            if len(organiser["organiser_affiliation"]) > 0:
                if organiser["affiliation_ror"] == "":
                    last_known_institutions = orga["last_known_institutions"]
                    max_similarity = 0
                    final_position = -1
                    if last_known_institutions is not None and len(last_known_institutions) > 0:
                        for institution_position, last_known_institution in enumerate(last_known_institutions):
                            institute_name = last_known_institution["display_name"]
                            institution_similarity = fuzz.token_set_ratio(institute_name,organiser["organiser_affiliation"])
                            if institution_similarity > max_similarity:
                                if DEBUG: print(f"{institute_name}; {institution_position}; {institution_similarity}")
                                max_similarity = institution_similarity
                                final_position = institution_position
                        if max_similarity >= 40:        
                            organiser_institution_from_OA = last_known_institutions[final_position]
                            organiser["affiliation_ror"] = organiser_institution_from_OA["ror"]
                            organiser["verified"] = True
                    else:
                        print(f"WARNING: for {json.dumps(organiser)} I have encountered issues in extracting the last know affiliation")
        print(organiser)
    
    return organisers


def match_conference_with_other_datasets(result:dict)->dict:
    """
    Matches the extracted conference series with external datasets (DBLP, AIDA, ConfIDent).

    It uses semantic similarity (SentenceTransformer) to find candidate matches in pre-loaded
    FAISS indices, and then verifies/refines matches using Levenshtein distance.

    Args:
        result (dict): The conference data dictionary.

    Returns:
        dict: The updated dictionary with 'DBLP', 'AIDA', and 'ConfIDent' keys populated.
    """
    
    # Load a pretrained Sentence Transformer model
    model = SentenceTransformer("all-MiniLM-L6-v2")
    embeddings = model.encode([result["conference_series"]])
    
    # --- DBLP Matching ---
    with open('DBLP.pickle', 'rb') as handle:
        dblp_confs = pickle.load(handle)
    
    result["DBLP"]=dict()
    # Search in FAISS index
    D, I = dblp_confs["index"].search(embeddings, k=1)
    # Check distance threshold
    if D[0][0] <= 0.4:
        this_conf_dblp = dblp_confs["sentences"][I[0][0]]
        this_acronym_dblp = dblp_confs["confs"][this_conf_dblp]
        # print(this_conf_dblp)
        # print(this_acronym_dblp)
        # print(f"https://dblp.org/streams/conf/{urllib.parse.quote(this_acronym_dblp, safe='')}")
    else:
        this_conf_dblp = ""
        this_acronym_dblp = ""

    # --- AIDA Matching ---
    with open('AIDA.pickle', 'rb') as handle:
        aida_confs = pickle.load(handle)
    
    result["AIDA"]=dict()
    D, I = aida_confs["index"].search(embeddings, k=1)
    if D[0][0] <= 0.4:
        this_conf_aida = aida_confs["sentences"][I[0][0]]
        this_acronym_aida = aida_confs["confs"][this_conf_aida]
        # print(this_conf_aida)
        # print(this_acronym_aida)
        # print(f"https://w3id.org/aida/dashboard/cs/conference/{urllib.parse.quote(this_conf_aida, safe='')}")
    else:
        this_conf_aida = ""
        this_acronym_aida = ""
        

    # --- ConfIDent Matching ---
    with open('ConfIDent.pickle', 'rb') as handle:
        confident_confs = pickle.load(handle)
    
    result["ConfIDent"]=dict()
    D, I = confident_confs["index"].search(embeddings, k=1)
    if D[0][0] <= 0.4:
        this_conf_confident = confident_confs["sentences"][I[0][0]]
        this_id_confident = confident_confs["confs"][this_conf_confident]
        # print(this_conf_confident)
        # print(this_id_confident)
        # print(f"https://www.confident-conference.org/index.php/{urllib.parse.quote(this_id_confident, safe='')}")
    else:
        this_conf_confident = ""
        this_id_confident = ""
        

    # Calculate string similarity to determine the best match among the candidates
    similarity_dblp = Levenshtein.normalized_similarity(this_conf_dblp,result["conference_series"])
    similarity_aida = Levenshtein.normalized_similarity(this_conf_aida,result["conference_series"])
    similarity_confident = Levenshtein.normalized_similarity(this_conf_confident,result["conference_series"])

    # print(similarity_dblp,similarity_aida,similarity_confident)

    # Logic to prioritize the best match and propagate IDs across datasets if mappings exist
    
    # Case 1: DBLP is the best match
    if similarity_dblp >= max(similarity_aida,similarity_confident) and similarity_dblp > 0:
        # print("I am here 1")
        result["DBLP"]["name"]= this_conf_dblp
        result["DBLP"]["id"]  = this_acronym_dblp
        result["DBLP"]["url"] = f"https://dblp.org/streams/conf/{urllib.parse.quote(this_acronym_dblp, safe='')}"

        # Try to find AIDA match via DBLP acronym
        if this_acronym_dblp in aida_confs["dblp"]:
            this_conf_aida = aida_confs["dblp"][this_acronym_dblp]
            this_acronym_aida = this_acronym_dblp
    
            result["AIDA"]["name"]= this_conf_aida
            result["AIDA"]["id"]  = this_acronym_aida
            result["AIDA"]["url"] = f"https://w3id.org/aida/dashboard/cs/conference/{urllib.parse.quote(this_conf_aida, safe='')}"

        # Try to find ConfIDent match via DBLP acronym
        if this_acronym_dblp in confident_confs["dblp_confs"]:
            this_id_confident = confident_confs["dblp_confs"][this_acronym_dblp]
            this_conf_confident = confident_confs["confids"][this_id_confident]
            
            result["ConfIDent"]["name"]= this_conf_confident
            result["ConfIDent"]["id"]  = this_id_confident
            result["ConfIDent"]["url"] = f"https://www.confident-conference.org/index.php/{urllib.parse.quote(this_id_confident, safe='')}"

    # Case 2: AIDA is the best match
    if similarity_aida > max(similarity_dblp,similarity_confident):
        # print("I am here 2")
        # Try to find DBLP match via AIDA acronym
        if this_acronym_aida in dblp_confs["idsconfs"]:
            this_conf_dblp =  dblp_confs["idsconfs"][this_acronym_aida]
            this_acronym_dblp = this_acronym_aida

            result["DBLP"]["name"]= this_conf_dblp
            result["DBLP"]["id"]  = this_acronym_dblp
            result["DBLP"]["url"] = f"https://dblp.org/streams/conf/{urllib.parse.quote(this_acronym_dblp, safe='')}"
    
        result["AIDA"]["name"]= this_conf_aida
        result["AIDA"]["id"]  = this_acronym_aida
        result["AIDA"]["url"] = f"https://w3id.org/aida/dashboard/cs/conference/{urllib.parse.quote(this_conf_aida, safe='')}"

        # Try to find ConfIDent match via AIDA acronym
        if this_acronym_aida in confident_confs["dblp_confs"]:
            this_id_confident = confident_confs["dblp_confs"][this_acronym_dblp]
            this_conf_confident = confident_confs["confids"][this_id_confident]
        
            result["ConfIDent"]["name"]= this_conf_confident
            result["ConfIDent"]["id"]  = this_id_confident
            result["ConfIDent"]["url"] = f"https://www.confident-conference.org/index.php/{urllib.parse.quote(this_id_confident, safe='')}"

    # Case 3: ConfIDent is the best match
    if similarity_confident > max(similarity_aida,similarity_dblp):
        # print("I am here 3")
        if this_id_confident in confident_confs["event2dblp"]:
            dblp_id = confident_confs["event2dblp"][this_id_confident]
            
            # Map back to DBLP
            if dblp_id in dblp_confs["idsconfs"]:
                this_conf_dblp =  dblp_confs["idsconfs"][dblp_id]
                this_acronym_dblp = dblp_id
        
                result["DBLP"]["name"]= this_conf_dblp
                result["DBLP"]["id"]  = this_acronym_dblp
                result["DBLP"]["url"] = f"https://dblp.org/streams/conf/{urllib.parse.quote(this_acronym_dblp, safe='')}"
        
            # Map back to AIDA
            if dblp_id in aida_confs["dblp"]:
                this_conf_aida = aida_confs["dblp"][dblp_id]
                this_acronym_aida = dblp_id
            
                result["AIDA"]["name"]= this_conf_aida
                result["AIDA"]["id"]  = this_acronym_aida
                result["AIDA"]["url"] = f"https://w3id.org/aida/dashboard/cs/conference/{urllib.parse.quote(this_conf_aida, safe='')}"
    
        result["ConfIDent"]["name"]= this_conf_confident
        result["ConfIDent"]["id"]  = this_id_confident
        result["ConfIDent"]["url"] = f"https://www.confident-conference.org/index.php/{urllib.parse.quote(this_id_confident, safe='')}"

    return result

def process_call_for_papers(call_for_papers:str)->dict:
    """
    Processes the call for papers from unstructured to structured data.
    
    1. Creates an instance of connection to the remote model.
    2. Requests the model to process the call for papers
    3. Process all organisers with OpenAlex api
    4. Find mapping towards other conference datasets
    5. Return
    

    Parameters
    ----------
    call_for_papers : str
        the call for papers in a single string format.

    Returns
    -------
    dict
        the dictionary containing all the relevant and structured info about the call for papers.

    """
    
    client = connect_to_OpenRouter()
    print("Connected to remote model")
    result = run_model(client, call_for_papers)
    print("Finished running model")
    result["organisers"] = get_authors_info_from_openalex(result["organisers"])
    print("Completed processing organisers via OpenAlex")
    result = match_conference_with_other_datasets(result)
    print("Mapped the conference to other datasets")
    return result
    