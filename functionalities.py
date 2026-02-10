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
import country_converter as coco
from sentence_transformers import SentenceTransformer


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
    text_prompt = f"""In this prompt, you will receive a Call for Papers of a scientific event. Your task is to parse it, and identify some crucial elements.

    You must be exhaustive when extracting people. Extract **ALL** organisers, chairs, committee members, and track chairs listed in the text. Do not leave anyone out.
    
    For each person extracted:
    - 'organiser_name': The full name.
    - 'organiser_affiliation': The institution or company.
    - 'organiser_country': The country of the institution (infer if necessary/possible).
    - 'track_name': The specific role (e.g., 'General Chair', 'Program Chair') or the track they are associated with (e.g., 'Research Track', 'Demo Track'). If they are part of the general Program Committee, use 'Program Committee'.

    Extract:
    - the event name and its acronym;
    - the conference series;
    - any co-located events;
    - the year of the event;
    - the location of the event;
    - the list of topics of interest;
    - the list of all organisers/people.
                
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
              "year": {
                "type": "string",
                "description": "Year in which the event takes place. The only acceptable format is YYYY, such as 2024."
              },
              "location": {
                "type": "string",
                "description": "City or location name"
              },
              "topics": {
                "type": "array",
                "items": {
                    "type": "string"
                },
                "description": "A list of topics of interest, research areas, or submission categories mentioned in the Call for Papers."
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
                "description": "Identifies the name, affiliation (ideally including country) of ALL the conference organisers, chairs, and committee members."
              }
            },
            "required": ["event_name", "event_acronym", "conference_series", "colocated_with", "year", "location", "topics", "organisers"],
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
                
    # Post-processing: adding affiliation provenance
    for organiser in result["organisers"]:
        organiser["affiliation_provenance"] = "LLM"
        organiser["verified"] = False
    
    return result


def get_organisers_info_from_openalex(organisers:list, year:str)->list:
    """
    Enriches the organiser information by querying OpenAlex to retrieve author details and affiliations.

    This function attempts to identify each organiser in the OpenAlex database to fetch their
    OpenAlex ID, ORCID, and the ROR (Research Organization Registry) ID of their affiliation.
    
    The identification process follows a two-step strategy:
    1.  **Affiliation-based Search**: It first attempts to find the author by filtering for their 
        provided affiliation (institution). This is generally more accurate but relies on the 
        affiliation text being correctly parsed and present in OpenAlex.
    2.  **Name-based Search (Fallback)**: If the first step fails (e.g., affiliation is missing 
        or not matched), it searches by the author's name. To handle common names, it employs 
        heuristics such as prioritizing authors with a higher works count and using Levenshtein 
        similarity to match alternative names.

    Additionally, the function performs a quality check on the provided affiliations. If a high 
    degree of homogeneity is detected (suggesting a default or placeholder value was used for 
    all organisers), it clears the affiliation data to force a fresh lookup via OpenAlex.

    Parameters
    ----------
    organisers : list
        A list of dictionaries, where each dictionary represents an organiser and contains keys 
        like 'organiser_name', 'organiser_affiliation', etc.
    year : str
        The year of the conference. This is used to prioritize affiliations that are temporally 
        relevant to the event. Defaults to 2026 if None.

    Returns
    -------
    list
        The updated list of organisers, enriched with fields such as 'openalex_name', 
        'openalex_page', 'orcid', 'affiliation_ror', and 'verified'.

    """

    ### First we attempt to located the organiser by finding their affiliation, and filtering them by affiliation
    ### Second attempt is made when the affiliation is not clear.
    
    
    DEBUG = True
    
    # Set default year if not provided
    if year == None: year = 2026
    else: year = int(year)
    
    # Priority mapping for institution types to prefer academic/research institutions
    priority_types = {"education":0, "company":1, "facility":2, "healthcare":3, "funder":4, "government":5, "archive":6, "other":7}
    
    
    ###### CHECK QUALITY OF AFFILIATIONS
    # Sometimes LLMs hallucinate the same affiliation for everyone. We detect this by checking for low variance.
    
    to_clean = False
    list_of_institutions = list()
    for organiser in organisers:
        list_of_institutions.append(organiser["organiser_affiliation"])
    
    # Checking heterogeneity: if the number of total entries is much larger than unique entries, it might be suspicious.
    # Heuristic: if total items >= 4 * unique items, assume data is dirty.
    if len(list_of_institutions) >= len(set(list_of_institutions)) * 4: # static threshold which defines heterogeneity
        to_clean = True
        
        
    if to_clean:
        # Clear potentially incorrect affiliations to force OpenAlex lookup
        for organiser in organisers:
            organiser["organiser_affiliation"] = ""
            organiser["organiser_country"] = ""
            organiser["affiliation_ror"] = ""
            organiser["affiliation_provenance"] = ""
            
            
    ###### NOW PROCESSING EACH INDIVIDUAL ORGANISER
    
    
    for organiser in organisers:
        
        # Initialize fields for OpenAlex data
        organiser["openalex_name"] = ""
        organiser["openalex_page"] = ""
        organiser["orcid"] = ""
        organiser["affiliation_ror"] = ""
        organiser["verified"] = False
        

        if DEBUG: print(organiser)
        
        find_author_with_less_info = False
        openalex_matched_organiser = dict()
        
        ######## FINDING ORGANISER ON OPENALEX
        
        # Attempt 1: Search using Institution + Author Name
        if len(organiser["organiser_affiliation"]) > 0:
            if DEBUG: print(f"Found {len(organiser['organiser_affiliation'])} affiliations")
            # Search for the institution first to get its ID
            insts = Institutions().search(organiser["organiser_affiliation"]).get()
            if len(insts) > 0:
                inst_id = insts[0]["id"].replace("https://openalex.org/", "")
        
                # if "ror" in insts[0]["ids"]:
                #     organiser["affiliation_ror"] = insts[0]["ids"]["ror"]
                
                # Search for the author specifically within that institution
                auths = Authors().search(organiser["organiser_name"]).filter(affiliations={"institution":{"id": inst_id}}).get()
                if len(auths) > 0:        
                    if DEBUG: print(f"{len(auths)} search results found for the author")
                    openalex_matched_organiser = auths[0]
                else:
                    # Author not found in that institution, fallback to name-only search
                    find_author_with_less_info = True
                    if DEBUG: print(f"For {organiser['organiser_name']} I could not find a record")
                
                    
            else:
                # Institution not found, fallback to name-only search
                find_author_with_less_info = True
                if DEBUG: print(f"For {organiser['organiser_name']} I could not find a record of their institution")
        else:
            # No affiliation provided, fallback to name-only search
            find_author_with_less_info = True
            if DEBUG: print(f"For {organiser['organiser_name']} there is no affiliation")
    
        # Attempt 2: Search for authors without institution info (or if Attempt 1 failed)
        if find_author_with_less_info:
            auths = Authors().search(organiser['organiser_name']).get()
            if len(auths) == 1:
                # Exact single match
                openalex_matched_organiser = auths[0]
            elif len(auths) == 0:
                if DEBUG: print(f"For {organiser['organiser_name']} I could not find a record, AGAIN")
            else:
                if DEBUG: print(f"Found multiple records for {organiser['organiser_name']}")
                # Sort by works count to prioritize more prolific authors (heuristic)
                new_auths = sorted(auths, key=lambda item: item['works_count'], reverse=True)
    
                # Match the author with the most similar name (handling variations/typos)
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
    
                openalex_matched_organiser = new_auths[final_position] # contains the openalex record of the chosen person.
                
        
        # If an author record was found, populate the organiser dictionary
        if len(openalex_matched_organiser) > 0:
            organiser["openalex_name"] = openalex_matched_organiser["display_name"]
            organiser["openalex_page"] = openalex_matched_organiser["id"]
            organiser["orcid"] = ""
            
            # Extract ORCID if available
            if openalex_matched_organiser["orcid"] is not None:
                organiser["orcid"] = openalex_matched_organiser["orcid"]
            else:
                if "orcid" in openalex_matched_organiser["ids"] and openalex_matched_organiser["ids"]["orcid"] is not None:
                    organiser["orcid"] = openalex_matched_organiser["ids"]["orcid"]
            

            # Case A: No valid affiliation from LLM (or cleaned), try to infer from OpenAlex history
            if organiser["organiser_affiliation"] == "": 
                # now processing affiliations                    
                affiliations = openalex_matched_organiser["affiliations"]
                if DEBUG: print(f"Found {len(affiliations)} affiliations (FOR THIS AUTHOR I DON'T HAVE CLEAR AFFILIATION)")
                if affiliations is not None and len(affiliations) > 0:
                    affiliations_dict = dict()
                    # Analyze all past affiliations
                    for institution_position, affiliation in enumerate(affiliations):
                        affiliations_dict[institution_position] = {"pos":institution_position, 
                                                                  "display_name":affiliation["institution"]["display_name"],
                                                                  "type_priority":priority_types[affiliation["institution"]["type"]] if affiliation["institution"]["type"] in priority_types else 99, 
                                                                  "min_years":min([abs(year-i) for i in affiliation["years"]]), # Distance to conference year
                                                                  "activity":len(affiliation["years"])}
                        
                    # Sort affiliations by temporal proximity and then by institution type priority
                    sorted_affiliation_history = sorted(affiliations_dict, key=lambda k: (affiliations_dict[k]["min_years"],affiliations_dict[k]["type_priority"]))
                    
                    # Check if the most appropriate affiliation is close in time (within 10 years)
                    if affiliations_dict[sorted_affiliation_history[0]]["min_years"] <= 10:
                        most_appropriate_affiliation = affiliations[sorted_affiliation_history[0]]
                
                        # Update organiser with inferred affiliation
                        organiser["organiser_affiliation"]  = most_appropriate_affiliation["institution"]["display_name"]
                        organiser["affiliation_ror"]        = most_appropriate_affiliation["institution"]["ror"]
                        organiser["affiliation_provenance"] = "OA" # Provenance: OpenAlex
                        try:
                            organiser["organiser_country"] = coco.convert(names=[most_appropriate_affiliation["institution"]["country_code"]], to='name_short') 
                        except:
                            organiser["organiser_country"] = ""
                        # institution_similarity = fuzz.token_set_ratio(most_appropriate_affiliation["institution"]["display_name"],organiser["organiser_affiliation"])
                        # if institution_similarity >= 40:        
                        #     organiser["verified"] = True
                            
            
            
            # Case B: Affiliation exists (from LLM), try to verify and recover ROR
            elif len(organiser["organiser_affiliation"]) > 0: 
                if organiser["affiliation_ror"] == "": ## at this stage this always true
                    
                    max_similarity = 0
                    final_position = -1
                    
                    affiliations = openalex_matched_organiser["affiliations"]
                    if DEBUG: print(f"Found {len(affiliations)} affiliations (FOR THIS AUTHOR I ALREADY HOLD INFO ABOUT AFFILIATION)")
                    
                    # Fuzzy match the provided affiliation against the author's OpenAlex affiliation history
                    for institution_position, affiliation in enumerate(affiliations):
                        institution_similarity = fuzz.token_set_ratio(affiliation["institution"]["display_name"],organiser["organiser_affiliation"])
                        if DEBUG: print(f'{affiliation["institution"]["display_name"]}; {institution_position}; {institution_similarity}')
                        if institution_similarity > max_similarity:
                            if DEBUG: print(f'{affiliation["institution"]["display_name"]}; {institution_position}; {institution_similarity}')
                            max_similarity = institution_similarity
                            final_position = institution_position
                    
                    # If a good match is found, assign the ROR and mark as verified
                    if max_similarity >= 40:        
                        organiser_institution_from_OA = affiliations[final_position]["institution"]
                        organiser["affiliation_ror"] = organiser_institution_from_OA["ror"]
                        organiser["verified"] = True
                
                
        
        if DEBUG: print(organiser)
        if DEBUG: print("-------------------------")
    
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

def match_openalex_topics(result:dict)->dict:
    
    if len(result["topics"])>0:
        
        enhanced_topics = dict()
        dist_threshold = 0.6
        
        with open('openalex.pickle', 'rb') as handle:
            openalex = pickle.load(handle)
            
        # 1. Load a pretrained Sentence Transformer model
        emb_model = SentenceTransformer("all-MiniLM-L6-v2")
            
        for topic in result["topics"]:
            
            embeddings = emb_model.encode([topic])
        
            # Search the vector index for the top 5 similar topics
            # Assumes 'self.embedding_vectors["index"]' is a FAISS or similar index.
            dists, similar_items = openalex["index"].search(embeddings, k=5)
            
            for pos, returned_item in enumerate(similar_items[0]): 
                matched_topic = list()
                # Check if the semantic distance is within the threshold
                if dists[0][pos] <= dist_threshold:
                    matched_topic.append(openalex['sentences'][returned_item])
            
            
            enhanced_topics[topic] = matched_topic
            
        result["enhanced_topics"] = enhanced_topics
    
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
    
    # result = {"event_name": "30th Annual International Conference on Science and Technology Indicators", "year":"2026", "conference_series": "Science and Technology Indicators", "event_acronym": "STI-ENID 2026", "colocated_with": "", "location": "Antwerp", "organisers": [{"organiser_name": "Tim Engels", "organiser_affiliation": "ECOOM, University of Antwerp", "organiser_country": "Belgium", "track_name": "main"}, {"organiser_name": "Steven Van Passel", "organiser_affiliation": "ECOOM, University of Antwerp", "organiser_country": "Belgium", "track_name": "main"}, {"organiser_name": "Peter Aspeslagh", "organiser_affiliation": "ECOOM, University of Antwerp", "organiser_country": "Belgium", "track_name": "main"}, {"organiser_name": "Pei-Shan Chi", "organiser_affiliation": "ECOOM, University of Antwerp", "organiser_country": "Belgium", "track_name": "main"}, {"organiser_name": "Ine De Parade", "organiser_affiliation": "ECOOM, University of Antwerp", "organiser_country": "Belgium", "track_name": "main"}, {"organiser_name": "Dirk Derom", "organiser_affiliation": "ECOOM, University of Antwerp", "organiser_country": "Belgium", "track_name": "main"}, {"organiser_name": "Myroslava Hladchenko", "organiser_affiliation": "ECOOM, University of Antwerp", "organiser_country": "Belgium", "track_name": "main"}, {"organiser_name": "Bart Thijs", "organiser_affiliation": "ECOOM, University of Antwerp", "organiser_country": "Belgium", "track_name": "main"}, {"organiser_name": "Sandy Van Ael", "organiser_affiliation": "ECOOM, University of Antwerp", "organiser_country": "Belgium", "track_name": "main"}, {"organiser_name": "Eline Vandewalle", "organiser_affiliation": "ECOOM, University of Antwerp", "organiser_country": "Belgium", "track_name": "main"}, {"organiser_name": "Johanna Vanderstraeten", "organiser_affiliation": "ECOOM, University of Antwerp", "organiser_country": "Belgium", "track_name": "main"}, {"organiser_name": "Walter Ysebaert", "organiser_affiliation": "ECOOM, University of Antwerp", "organiser_country": "Belgium", "track_name": "main"}]}
    # result = {"event_name": "24th International Semantic Web Conference (ISWC 2025)", "conference_series": "International Semantic Web Conference", "event_acronym": "ISWC 2025", "colocated_with": "", "year": "2025", "location": "Nara, Japan", "organisers": [{"organiser_name": "Daniel Garijo", "organiser_affiliation": "Universidad Polit\u00e9cnica de Madrid", "organiser_country": "Spain", "track_name": "Research Track Chair"}, {"organiser_name": "Sabrina Kirrane", "organiser_affiliation": "Vienna University of Economics and Business", "organiser_country": "Austria", "track_name": "Research Track Chair"}, {"organiser_name": "Cogan Shimizu", "organiser_affiliation": "Wright State University", "organiser_country": "US", "track_name": "Resource Track Chair"}, {"organiser_name": "Angelo Salatino", "organiser_affiliation": "KMi, The Open University", "organiser_country": "UK", "track_name": "Resource Track Chair"}, {"organiser_name": "Maribel Acosta", "organiser_affiliation": "Technical University of Munich", "organiser_country": "Germany", "track_name": "In-Use Track Chair"}, {"organiser_name": "Andrea Giovanni Nuzzolese", "organiser_affiliation": "CNR - Institute of Cognitive Sciences and Technologies", "organiser_country": "Italy", "track_name": "In-Use Track Chair"}, {"organiser_name": "Gong Cheng", "organiser_affiliation": "Nanjing University", "organiser_country": "China", "track_name": "Posters and Demos Chair"}, {"organiser_name": "Shenghui Wang", "organiser_affiliation": "University of Twente", "organiser_country": "The Netherlands", "track_name": "Posters and Demos Chair"}, {"organiser_name": "Mayank Kejriwal", "organiser_affiliation": "University of Southern California", "organiser_country": "United States", "track_name": "Semantic Web Challenge Chair"}, {"organiser_name": "Pablo Mendes", "organiser_affiliation": "Upwork", "organiser_country": "United States", "track_name": "Semantic Web Challenge Chair"}, {"organiser_name": "Blerina Spahiu", "organiser_affiliation": "University of Milano-Bicocca", "organiser_country": "Italy", "track_name": "Workshop Chair & Dagstuhl Style Workshop Chair & Tutorial Chair"}, {"organiser_name": "Juan Sequeda", "organiser_affiliation": "data.world", "organiser_country": "USA", "track_name": "Workshop Chair & Dagstuhl Style Workshop Chair & Tutorial Chair"}, {"organiser_name": "Oktie Hassanzadeh", "organiser_affiliation": "IBM Research", "organiser_country": "US", "track_name": "Industry Track Chair"}, {"organiser_name": "Irene Celino", "organiser_affiliation": "Cefriel", "organiser_country": "Italy", "track_name": "Industry Track Chair"}, {"organiser_name": "Abraham Bernstein", "organiser_affiliation": "University of Zurich", "organiser_country": "Switzerland", "track_name": "Doctoral Consortium Track Chair"}, {"organiser_name": "Natasha Noy", "organiser_affiliation": "Google Research", "organiser_country": "US", "track_name": "Doctoral Consortium Track Chair"}]}
    # result = {"event_name": "24th International Semantic Web Conference (ISWC 2025)", "conference_series": "International Semantic Web Conference", "event_acronym": "ISWC 2025", "colocated_with": "", "year": "2025", "location": "Nara, Japan", "organisers": [{"organiser_name": "Daniel Garijo", "organiser_affiliation": "Universidad Polit\u00e9cnica de Madrid", "organiser_country": "Spain", "track_name": "Research Track Chair", "affiliation_provenance": "LLM"}, {"organiser_name": "Sabrina Kirrane", "organiser_affiliation": "Vienna University of Economics and Business", "organiser_country": "Austria", "track_name": "Research Track Chair", "affiliation_provenance": "LLM"}, {"organiser_name": "Cogan Shimizu", "organiser_affiliation": "Wright State University", "organiser_country": "United States", "track_name": "Resource Track Chair", "affiliation_provenance": "LLM"}, {"organiser_name": "Angelo Salatino", "organiser_affiliation": "KMi, The Open University", "organiser_country": "United Kingdom", "track_name": "Resource Track Chair", "affiliation_provenance": "LLM"}, {"organiser_name": "Maribel Acosta", "organiser_affiliation": "Technical University of Munich", "organiser_country": "Germany", "track_name": "In-Use Track Chair", "affiliation_provenance": "LLM"}, {"organiser_name": "Andrea Giovanni Nuzzolese", "organiser_affiliation": "CNR - Institute of Cognitive Sciences and Technologies", "organiser_country": "Italy", "track_name": "In-Use Track Chair", "affiliation_provenance": "LLM"}, {"organiser_name": "Gong Cheng", "organiser_affiliation": "Nanjing University", "organiser_country": "China", "track_name": "Posters and Demos Chair", "affiliation_provenance": "LLM"}, {"organiser_name": "Shenghui Wang", "organiser_affiliation": "University of Twente", "organiser_country": "Netherlands", "track_name": "Posters and Demos Chair", "affiliation_provenance": "LLM"}, {"organiser_name": "Mayank Kejriwal", "organiser_affiliation": "University of Southern California", "organiser_country": "United States", "track_name": "Semantic Web Challenge Chair", "affiliation_provenance": "LLM"}, {"organiser_name": "Pablo Mendes", "organiser_affiliation": "Upwork", "organiser_country": "United States", "track_name": "Semantic Web Challenge Chair", "affiliation_provenance": "LLM"}, {"organiser_name": "Blerina Spahiu", "organiser_affiliation": "University of Milano-Bicocca", "organiser_country": "Italy", "track_name": "Workshop Chair", "affiliation_provenance": "LLM"}, {"organiser_name": "Juan Sequeda", "organiser_affiliation": "data.world", "organiser_country": "United States", "track_name": "Workshop Chair", "affiliation_provenance": "LLM"}, {"organiser_name": "Oktie Hassanzadeh", "organiser_affiliation": "IBM Research", "organiser_country": "United States", "track_name": "Industry Track Chair", "affiliation_provenance": "LLM"}, {"organiser_name": "Irene Celino", "organiser_affiliation": "Cefriel", "organiser_country": "Italy", "track_name": "Industry Track Chair", "affiliation_provenance": "LLM"}, {"organiser_name": "Abraham Bernstein", "organiser_affiliation": "University of Zurich", "organiser_country": "Switzerland", "track_name": "Doctoral Consortium Track Chair", "affiliation_provenance": "LLM"}, {"organiser_name": "Natasha Noy", "organiser_affiliation": "Google Research", "organiser_country": "United States", "track_name": "Doctoral Consortium Track Chair", "affiliation_provenance": "LLM"}]}
    # result = {"event_name": "30th Annual Conference on Science and Technology Indicators", "conference_series": "Science and Technology Indicators Conference", "event_acronym": "STI-ENID 2026", "colocated_with": "ECOOM", "year": "2026", "location": "Antwerp", "organisers": [{"organiser_name": "Tim Engels", "organiser_affiliation": "University of Antwerp", "organiser_country": "Belgium", "track_name": "Co-Chair", "affiliation_provenance": "LLM", "verified": False}, {"organiser_name": "Steven Van Passel", "organiser_affiliation": "University of Antwerp", "organiser_country": "Belgium", "track_name": "Co-Chair", "affiliation_provenance": "LLM", "verified": False}, {"organiser_name": "Peter Aspeslagh", "organiser_affiliation": "University of Antwerp", "organiser_country": "Belgium", "track_name": "Organizing Committee", "affiliation_provenance": "LLM", "verified": False}, {"organiser_name": "Pei-Shan Chi", "organiser_affiliation": "ECOOM", "organiser_country": "Belgium", "track_name": "Organizing Committee", "affiliation_provenance": "LLM", "verified": False}, {"organiser_name": "Ine De Parade", "organiser_affiliation": "ECOOM", "organiser_country": "Belgium", "track_name": "Organizing Committee", "affiliation_provenance": "LLM", "verified": False}, {"organiser_name": "Dirk Derom", "organiser_affiliation": "ECOOM", "organiser_country": "Belgium", "track_name": "Organizing Committee", "affiliation_provenance": "LLM", "verified": False}, {"organiser_name": "Myroslava Hladchenko", "organiser_affiliation": "ECOOM", "organiser_country": "Belgium", "track_name": "Organizing Committee", "affiliation_provenance": "LLM", "verified": False}, {"organiser_name": "Bart Thijs", "organiser_affiliation": "ECOOM", "organiser_country": "Belgium", "track_name": "Organizing Committee", "affiliation_provenance": "LLM", "verified": False}, {"organiser_name": "Sandy Van Ael", "organiser_affiliation": "ECOOM", "organiser_country": "Belgium", "track_name": "Organizing Committee", "affiliation_provenance": "LLM", "verified": False}, {"organiser_name": "Eline Vandewalle", "organiser_affiliation": "ECOOM", "organiser_country": "Belgium", "track_name": "Organizing Committee", "affiliation_provenance": "LLM", "verified": False}, {"organiser_name": "Johanna Vanderstraeten", "organiser_affiliation": "ECOOM", "organiser_country": "Belgium", "track_name": "Organizing Committee", "affiliation_provenance": "LLM", "verified": False}, {"organiser_name": "Walter Ysebaert", "organiser_affiliation": "ECOOM", "organiser_country": "Belgium", "track_name": "Organizing Committee", "affiliation_provenance": "LLM", "verified": False}]}
    print(json.dumps(result))
    
    result["organisers"] = get_organisers_info_from_openalex(result["organisers"], result["year"])
    print("Completed processing organisers via OpenAlex")
    result = match_conference_with_other_datasets(result)
    print("Mapped the conference to other datasets")
    result = match_openalex_topics(result)
    print(result["topics"])
    print("Mapped the topics of interest to OpenAlex Topics")
    print(result["enhanced_topics"])
    return result
    