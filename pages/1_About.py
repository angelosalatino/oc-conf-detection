#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import streamlit as st
from classes.visualiser import CoreVisualiser

if 'config' not in st.session_state:
    st.write("Please visit the main page first to load the configuration.")
    st.stop()

config = st.session_state['config']
vis = CoreVisualiser()

st.set_page_config(
    layout="wide",
    page_title=f"About {config['APP']['app_acronym']}",
    page_icon="🌐",
)

### WEBAPP
vis.local('assets/css/bootstrap.min.css')
vis.local('assets/css/mycss.css')

with st.sidebar:
    vis.add_logo()

st.markdown(
    f"""
    # About the {config['APP']['app_name']}
    
    The **{config['APP']['app_name']}** is a powerful, AI-driven tool designed to streamline the process of extracting critical information from academic **Call for Papers (CfPs)**. This tool automates the tedious task of manually parsing documents to identify conference details, series, locations, and, most importantly, the organising committee members.
    
    By using cutting-edge AI technology, this tool saves researchers and administrators countless hours, allowing them to quickly access and analyse key data points about academic events and their organisers. The tool works by taking a CfP as input and outputting a structured JSON object, making the data easily searchable, shareable, and integrable with other systems.
    
    ---
    
    **Table of Contents**
    - [Processing Modes](#processing-modes)
    - [Key Data Extracted](#key-data-extracted)
    - [Organiser Details](#organiser-details)
    - [Integration and Data Mapping](#integration-and-data-mapping)
    - [Topic Extraction and OpenAlex Matching](#topic-extraction-and-open-alex-matching)
    - [Organiser Matching Process](#organiser-matching-process)
    - [Intelligent CfP Rendering](#intelligent-cf-p-rendering)
    - [Rebranding COCI](#rebranding-coci)
    - [The Team](#the-team)
    
    ---
    
    ### Processing Modes
    
    To optimize processing time and API costs, the tool offers three distinct execution modes when uploading a Call for Papers:
    
    - **Cached**: If the file has been processed before, the tool instantly loads the fully enriched, finalized results from the local JSON cache.
    - **Mild Force**: The tool retrieves the pristine, raw metadata extraction from the LLM cache, but forces a complete re-run of the external OpenAlex and FAISS matching pipelines. This allows you to fetch updated database matches without running another LLM execution.
    - **Force**: Bypasses the cache entirely, triggering a fresh LLM extraction and a complete top-to-bottom re-processing of the document.
    
    ---
    
    ### Key Data Extracted
    
    The tool is built to recognise and extract the following core components from a CfP:
    
    - **`event_name`**: The full, official title of the conference or workshop.
    - **`conference_series`**: The name of the recurring conference series, without the year or edition number.
    - **`event_acronym`**: The short, official acronym for the event (e.g., "ICML," "CHI").
    - **`colocated_with`**: If the event is held in conjunction with another larger event, this field captures that information.
    - **`year`**: The year in which the event takes place.
    - **`location`**: The specific city or location where the event is scheduled to take place.
    - **`organisers`**: An array of objects, each containing detailed information about a committee member.
    
    ---
    
    ### Organiser Details
    
    Within the `organisers` array, the tool provides a rich set of information for each individual:
    
    - **`organiser_name`**: The full name of the organiser.
    - **`organiser_affiliation`**: The academic institution or company the organiser is affiliated with. Verified affiliations are marked with a star (✪).
    - **`organiser_country`**: The country of the organiser's affiliation, if available.
    - **`track_name`**: The specific track or area of the conference the organiser is involved in. For single-track events, the default value is 'main'.
    
    ### Integration and Data Mapping
    
    To further enrich the extracted information, the **{config['APP']['app_name']}** integrates with several well-known academic databases.
    
    - **OpenAlex**: Organiser names are mapped to OpenAlex, a global, open index of scholarly literature and researchers. This allows the tool to identify additional identifiers like **ORCIDs** and **RORs** (Research Organisation Registry identifiers) for institutions.
    - **DBLP, AIDA Dashboard, and Conference ConfIDent**: Conference details are mapped to these databases to provide a comprehensive view of the event's history and relevance within the scientific community.
    
    ---
    
    ### Topic Extraction and OpenAlex Matching
    
    In addition to capturing event metadata and organisers, COCI identifies the core research themes of the conference.
    
    1. **Raw Extraction**: The tool first extracts a list of topics of interest, research areas, or submission categories explicitly mentioned in the Call for Papers.
    2. **Semantic Encoding**: Each raw topic is encoded into a high-dimensional semantic vector using a pre-trained SentenceTransformer model.
    3. **Vector Search**: The system queries a FAISS vector index containing all standardized OpenAlex topics to find the closest semantic matches for each raw topic.
    4. **Enrichment**: The original extracted topics are then mapped to these standardized OpenAlex concepts, enabling better categorization, interoperability, and trend analysis.
    
    **Interactive Topic Thresholding:**
    Within the results page, users can dynamically adjust the **Similarity Distance Threshold** via an interactive slider. This allows you to strictly filter or broadly expand the semantic topic matches on the fly, instantly recalculating results without needing to reprocess the entire document.

    ---
    
    ### Organiser Matching Process
    
    The tool employs a sophisticated multi-stage process to match extracted organisers with their OpenAlex profiles:
    
    1. **Quality Check**: First, the system evaluates the provided affiliations for diversity. If they appear too homogeneous (suggesting a default value), they are discarded to force a broader search.
    2. **Profile Search**:
        - **Affiliation-Based**: The system attempts to locate the author within their specific institution in OpenAlex.
        - **Name-Based Fallback**: If the affiliation search fails, it searches by name, using publication count and name similarity to identify the most likely candidate.
    3. **Verification and Enrichment**:
        - **Verification**: If an affiliation was provided, it is cross-referenced with the author's publication history. Validated matches are marked with a star (✪).
        - **Inference**: If no affiliation was provided, the system infers the most likely current affiliation based on recent publication history.
        - **ID Extraction**: Finally, ORCID and ROR (Research Organization Registry) identifiers are retrieved.
        
    <br>
    <div style="text-align: center;">
        <img src="{vis.get_image_as_base64('assets/images/flowchart.png')}" alt="Architectural flow of the matching process" width="500" style="max-width: 100%; border: 1px solid #ddd; border-radius: 5px;"/>
        <p style="color: gray; font-size: 14px; margin-top: 10px;"><i>Architectural flow of the matching process</i></p>
    </div>
    <br>

    ---
        
    ### Intelligent CfP Rendering
    
    The tool features a dedicated "Read Call for Papers" tab that employs a custom rendering engine. It preserves the author's original plain-text formatting (translating tabs and spacing into beautifully structured bullet points) while intelligently detecting and linkifying all URLs and emails, making the raw text fully interactive and easily readable.

    ---
    
    ### Rebranding COCI
    _(note from 10 Feb 2026)_
    
    By simply changing "Organising Committee" to "Organisers and Content", we have shifted the focus from a narrow group of people to a broader spectrum of information without losing the brand equity of COCI.
    
    ---
    
    ### The Team
    
    This tool has been brought to you by the **Knowledge Media Institute** of the **Open University** in collaboration with **Springer Nature**.
    
    For any information or questions, please contact **Angelo Salatino** at angelo dot salatino at open dot ac dot uk.
    """, unsafe_allow_html=True
)

vis.render_footer()