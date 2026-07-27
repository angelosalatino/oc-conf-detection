#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
os.environ['FAISS_OPT_LEVEL'] = ''  # do this BEFORE importing any faiss library

import streamlit as st
import configparser
import pymongo
from rapidfuzz import fuzz
from pathlib import Path

from classes.visualiser import ConferenceVisualiser
from classes.conference import Conference
from classes.storage import ConferenceStorage

# Ensure configuration is loaded
if 'config' not in st.session_state:
    st.session_state['config'] = configparser.ConfigParser()
    st.session_state['config'].read('config.ini')

config = st.session_state['config']
vis = ConferenceVisualiser()

def check_page_change(page_name):
    if 'current_page' not in st.session_state:
        st.session_state['current_page'] = page_name
    elif st.session_state['current_page'] != page_name:
        st.session_state['current_page'] = page_name
        keys_to_clear = [
            'selected_event_id', 'selected_organiser_key', 
            'search_mode', 'search_term', 
            'org_search_mode', 'org_search_term',
            'selected_openalex_author', 'openalex_search_query'
        ]
        for key in keys_to_clear:
            if key in st.session_state:
                del st.session_state[key]

check_page_change("explore_events")

# Page configuration
st.set_page_config(
    layout="wide",
    page_title=f"Explore Events - {config['APP']['app_acronym']}",
    page_icon="🌐",
)

# Load CSS resources
vis.local('assets/css/bootstrap.min.css')
vis.local('assets/css/mycss.css')

with st.sidebar:
    vis.add_logo()

# Check storage settings to ensure MongoDB is enabled
storage_type = config.get('STORAGE', 'type', fallback='file')
storage_type = storage_type.split('#')[0].split(';')[0].strip()

if storage_type not in ['mongodb', 'both']:
    st.warning("⚠️ The **Explore Events** search page requires MongoDB to be active. Please enable it by setting `type = mongodb` or `type = both` in the `[STORAGE]` section of your `config.ini` file.")
    vis.render_footer()
    st.stop()

# Connect to MongoDB
uri = config.get('MONGODB', 'uri', fallback='mongodb://localhost:27017/')
db_name = config.get('MONGODB', 'db_name', fallback='coci')

try:
    client = pymongo.MongoClient(uri, serverSelectionTimeoutMS=2000)
    client.server_info()  # Triggers exception if connection fails
    db = client[db_name]
except Exception as e:
    st.error(f"❌ Failed to connect to the MongoDB server. Please verify that your MongoDB service is running on `{uri}`. Error details: {e}")
    vis.render_footer()
    st.stop()

# ----------------- EVENT DETAILS VIEW -----------------
if 'selected_event_id' in st.session_state:
    selected_id = st.session_state['selected_event_id']
    event_doc = db["events"].find_one({"_id": selected_id})
    
    if not event_doc:
        st.error(f"Event with ID {selected_id} not found in the database.")
        if st.button("← Back to search results"):
            del st.session_state['selected_event_id']
            st.rerun()
    else:
        if st.button("← Back to search results", type="secondary"):
            del st.session_state['selected_event_id']
            st.rerun()
        
        st.divider()
        conf = Conference.from_dict(event_doc.get("processed", {}))
        dest_folder = config.get('FOLDERS', 'destination_folder', fallback='processed_cfps')
        storage = ConferenceStorage(dest_folder)
        filenames = event_doc.get("filenames", [])
        filename = filenames[0] if filenames else f"event_{selected_id}"
        
        # Check if there is a CFP text saved
        cfps = event_doc.get("cfps", [])
        
        cfp_text = ""
        if isinstance(cfps, list):
            try:
                idx = filenames.index(filename)
                if idx < len(cfps):
                    cfp_text = cfps[idx]
            except ValueError:
                if cfps:
                    cfp_text = cfps[0]
        elif isinstance(cfps, dict):
            cfp_text = cfps.get(filename, "")
            if not cfp_text and cfps:
                cfp_text = next(iter(cfps.values()))
            
        if cfp_text:
            tab1, tab2 = st.tabs(["**Results**", "**Read Call for Papers**"])
            with tab1:
                vis.display_main(conf, filename, storage)
            with tab2:
                from classes.call_for_paper import CallForPaper
                cfp_obj = CallForPaper(cfp_text)
                st.html(cfp_obj.get_rendered_html())
        else:
            vis.display_main(conf, filename, storage)

# ------------------ LIST & SEARCH VIEW ------------------
else:
    st.markdown("<div id='top' style='height: 40px;'></div>", unsafe_allow_html=True)
    st.title("Explore Events in COCI")
    st.markdown("Search for processed calls for papers by keyword, acronym, or series, or click **I'm feeling lucky** to display the last 10 events added.")

    # Centered Search controls
    col1, col2, col3 = st.columns([1, 3, 1])
    with col2:
        search_query = st.text_input("Search events", placeholder="e.g. Semantic Web ...", label_visibility="collapsed")
        
        btn_col1, btn_col2 = st.columns([1, 1])
        with btn_col1:
            search_clicked = st.button("Search", use_container_width=True, type="primary")
        with btn_col2:
            lucky_clicked = st.button("I'm feeling lucky", use_container_width=True)

    # Manage search states in session_state so results persist during interactions
    if 'search_mode' not in st.session_state:
        st.session_state['search_mode'] = None
    if 'search_term' not in st.session_state:
        st.session_state['search_term'] = ''

    if search_clicked:
        st.session_state['search_mode'] = 'search'
        st.session_state['search_term'] = search_query.strip()
    elif lucky_clicked:
        st.session_state['search_mode'] = 'lucky'
        st.session_state['search_term'] = ''

    mode = st.session_state.get('search_mode')
    results = []

    if mode == 'lucky':
        results = list(db["events_index"].find().sort([("index", -1)]).limit(10))
        st.subheader("Last 10 events added to the system")
    elif mode == 'search':
        query = st.session_state.get('search_term', '').strip()
        if not query:
            st.warning("Please enter a query in the search box first.")
        else:
            # Load event records to search by topics in addition to name and series
            all_events = list(db["events"].find({}, {
                "_id": 1,
                "index": 1,
                "processed.event_name": 1,
                "processed.event_acronym": 1,
                "processed.conference_series": 1,
                "processed.year": 1,
                "processed.topics": 1
            }))
            matched = []
            
            for doc in all_events:
                processed = doc.get("processed", {})
                name = processed.get("event_name", "")
                acronym = processed.get("event_acronym", "")
                series = processed.get("conference_series", "")
                year = processed.get("year", "")
                topics = processed.get("topics", [])
                idx = doc.get("index") or doc.get("_id")
                
                # Check fuzzy similarities
                name_score = fuzz.WRatio(query.lower(), name.lower())
                acronym_score = fuzz.WRatio(query.lower(), acronym.lower())
                series_score = fuzz.WRatio(query.lower(), series.lower())
                
                # Check topics similarities
                topic_score = 0
                best_topic = ""
                for t in topics:
                    t_score = fuzz.WRatio(query.lower(), t.lower())
                    if t_score > topic_score:
                        topic_score = t_score
                        best_topic = t
                
                max_score = max(name_score, acronym_score, series_score, topic_score)
                
                if max_score >= 60:  # Relevancy threshold (stricter 60% match score)
                    match_reason = ""
                    if max_score == topic_score and topic_score > 70:
                        match_reason = f"Matched topic: *'{best_topic}'*"
                        
                    matched.append({
                        "index": idx,
                        "event_name": name,
                        "event_acronym": acronym,
                        "conference_series": series,
                        "year": year,
                        "similarity": max_score,
                        "match_reason": match_reason
                    })
            
            # Sort by similarity score descending, and then by Index ID descending
            matched.sort(key=lambda x: (x.get("similarity", 0), x.get("index", 0)), reverse=True)
            results = matched
            st.subheader(f"Search results for '{query}' ({len(results)} matches)")

    # Display list of events
    if mode == 'lucky' or (mode == 'search' and st.session_state.get('search_term', '').strip()):
        if not results:
            st.info("No matching events found in the database.")
        else:
            for doc in results:
                idx = doc["index"]
                name = doc.get("event_name", "Unknown Event")
                year = doc.get("year", "")
                series = doc.get("conference_series", "")
                match_reason = doc.get("match_reason", "")
                
                similarity_badge = ""
                if "similarity" in doc:
                    similarity_badge = f" :blue-badge[Match score: {doc['similarity']:.1f}%]"

                with st.container(border=True):
                    info_col, btn_col = st.columns([5, 1], vertical_alignment="center")
                    with info_col:
                        st.markdown(f"#### {series} ({year}){similarity_badge}")
                        if series and series != name:
                            st.markdown(f"**Series**: {series}")
                        if match_reason:
                            st.markdown(f"💡 {match_reason}")
                        st.markdown(f"**ID / Index**: {idx}")
                    with btn_col:
                        if st.button("View Event", key=f"view_btn_{idx}", type="primary", use_container_width=True):
                            st.session_state['selected_event_id'] = idx
                            st.rerun()

    # Anchor to scroll up
    st.markdown(
        """
        <a href="#top" title="Scroll to top" style="
            position: fixed;
            bottom: 120px;
            right: 30px;
            background-color: #183642;
            color: white;
            border-radius: 50%;
            width: 50px;
            height: 50px;
            display: flex;
            justify-content: center;
            align-items: center;
            font-size: 24px;
            text-decoration: none;
            box-shadow: 0 4px 6px rgba(0,0,0,0.3);
            z-index: 999999;
        ">↑</a>
        """, unsafe_allow_html=True
    )

vis.render_footer()
