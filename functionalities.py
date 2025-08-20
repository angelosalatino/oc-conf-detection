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



def create_destination_path(filename:str)->str:
    cut_filename = Path(filename).stem
    return f"{st.session_state['config']['FOLDERS']['destination_folder']}/{cut_filename}.json"

def check_if_file_was_previously_processed(filename:str)->str:
    complete_path = create_destination_path(filename)
    my_file = Path(complete_path)
    if my_file.is_file():
        return True
    else:
        return False


def read_config_file():
    if 'config' not in st.session_state:
        st.session_state['config'] = configparser.ConfigParser()
        st.session_state['config'].read('config.ini')
    

def connect_to_OpenRouter():
    api_url = st.session_state['config']['DEFAULT']['api_url']
    api_key = st.session_state['config']['DEFAULT']['api_key']
    if len(api_key) == 0:
        print("API Key missing!")
    client = OpenAI(
      base_url=api_url,
      api_key=api_key,
    )
    return client

def prepare_prompt(call_for_papers:str)->str:
    text_prompt = f"""In this prompt, you will receive a Call for Papers of a scientific event. Your task is to parse it, and identify some crucial elements:

                - the event name and its acronym;
                - the location of the event
                - the organisers of the event
                
                <call_for_papers>
                {call_for_papers}
                </call_for_papers>"""
    return text_prompt
                
def run_model(client:OpenAI, call_for_papers:str)->dict:
                            
    text_prompt = prepare_prompt(call_for_papers=call_for_papers)
                
    true = True
    false = False
    extra_headers={
        "HTTP-Referer": st.session_state['config']['TEAM']['website'], # Optional. Site URL for rankings on openrouter.ai.
        "X-Title": st.session_state['config']['TEAM']['description'], # Optional. Site title for rankings on openrouter.ai.
        }
    model="openai/gpt-4o"
    messages= [
        { "role": "user", "content": text_prompt }
        ]
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
                "description": "This refers to the name of a conference series, which is a collection of events that happen on a regular basis. It's usually similar to the event's name, but without the edition number or the year."
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
                                "description": "This identifies the main track in which the organiser is involved. A conference may have several tracks, whereas a workshop may have one single track. As default you shall use 'main'."
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
    
    completion = client.chat.completions.create(extra_headers=extra_headers, 
                                            model=model, 
                                            messages=messages, 
                                            response_format=response_format)
    result = json.loads(completion.choices[0].message.content)
    return result


def get_authors_info_from_openalex(organisers:list)->list:
    """
    
    This is a convoluted algorithm. 
    First it attempts a double filtering (institution + authorname), for a more precise outcome.
    However, as in many cases it fails (affiliations in CfP are not similar to the institution name in OpenAlex), 
    we simply retrieve author info based on their name, and try to find the correct authors within the returned pool.
    
    

    Parameters
    ----------
    organisers : list
        list of organisers.

    Returns
    -------
    list
        the same list of organisers with augmented information from OpenAlex.

    """

    ### First we attempt to located the organiser by finding their affiliation, and filtering them by affiliation
    ### Second attempt is made when the affiliation is not clear.
    
    
    DEBUG = False
    for organiser in organisers:
        
        organiser["openalex_name"] = ""
        organiser["openalex_page"] = ""
        organiser["orcid"] = ""
        organiser["affiliation_ror"] = ""
        
        find_author_with_less_info = False
        orga = {}
        
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
    
        # Search for authors without institution info
        if find_author_with_less_info:
            auths = Authors().search(organiser['organiser_name']).get()
            if len(auths) == 1:
                orga = auths[0]
            elif len(auths) == 0:
                if DEBUG: print(f"For {organiser['organiser_name']} I could not find a record, AGAIN")
            else:
                if DEBUG: print(f"Found multiple records for {organiser['organiser_name']}")
                new_auths = sorted(auths, key=lambda item: item['works_count'], reverse=True)
    
                # this algorithm makes sure we match the author with the most similar name
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
    
        if len(orga) > 0:
            organiser["openalex_name"] = orga["display_name"]
            organiser["openalex_page"] = orga["id"]
            organiser["orcid"] = orga["orcid"]
            if organiser["affiliation_ror"] == "":
                last_known_institutions = orga["last_known_institutions"]
                max_similarity = 0
                final_position = -1
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
    
    return organisers


def match_conference_with_other_datasets(result:dict)->dict:
    
    # Load a pretrained Sentence Transformer model
    model = SentenceTransformer("all-MiniLM-L6-v2")
    embeddings = model.encode([result["conference_series"]])
    
    with open('DBLP.pickle', 'rb') as handle:
        dblp_confs = pickle.load(handle)
    
    result["DBLP"]=dict()
    D, I = dblp_confs["index"].search(embeddings, k=1)
    if D[0][0] <= 0.4:
        this_conf = dblp_confs["sentences"][I[0][0]]
        this_acronym = dblp_confs["confs"][this_conf]
        # print(this_conf)
        # print(this_acronym)
        # print(f"https://dblp.org/streams/conf/{urllib.parse.quote(this_acronym, safe='')}")
        result["DBLP"]["name"]= this_conf
        result["DBLP"]["id"]  = this_acronym
        result["DBLP"]["url"] = f"https://dblp.org/streams/conf/{urllib.parse.quote(this_acronym, safe='')}"
        
        
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
        result["AIDA"]["name"]= this_conf_aida
        result["AIDA"]["id"]  = this_acronym_aida
        result["AIDA"]["url"] = f"https://w3id.org/aida/dashboard/cs/conference/{urllib.parse.quote(this_conf_aida, safe='')}"


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
    