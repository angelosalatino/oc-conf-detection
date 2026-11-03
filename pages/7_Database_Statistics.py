#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
os.environ['FAISS_OPT_LEVEL'] = ''

import streamlit as st
import configparser
import pymongo
import pandas as pd
from collections import Counter
from datetime import datetime

from classes.visualiser import ConferenceVisualiser

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

check_page_change("database_statistics")

# Page configuration
st.set_page_config(
    layout="wide",
    page_title=f"Statistics - {config['APP']['app_acronym']}",
    page_icon="📊",
)

# Load CSS resources
vis.local('assets/css/bootstrap.min.css')
vis.local('assets/css/mycss.css')

with st.sidebar:
    vis.add_logo()

# Check storage settings to ensure MongoDB is enabled
storage_type = config.get('STORAGE', 'type', fallback='file')
storage_type = storage_type.split('#')[0].split(';')[0].strip().lower()

if storage_type not in ['mongodb', 'both']:
    st.warning("⚠️ The **Statistics** page requires MongoDB to be active. Please enable it by setting `type = mongodb` or `type = both` in the `[STORAGE]` section of your `config.ini` file.")
    vis.render_footer()
    st.stop()

# Connect to MongoDB
uri = config.get('MONGODB', 'uri', fallback='mongodb://localhost:27017/')
db_name = config.get('MONGODB', 'db_name', fallback='coci')

try:
    client = pymongo.MongoClient(uri, serverSelectionTimeoutMS=2000)
    client.server_info()
    db = client[db_name]
except Exception as e:
    st.error(f"❌ Failed to connect to MongoDB server at `{uri}`: {e}")
    vis.render_footer()
    st.stop()

st.markdown("<div id='top' style='height: 20px;'></div>", unsafe_allow_html=True)
st.title("📊 Database Statistics & Insights")
st.markdown("Overview of all conferences, organisers, topics, and external knowledge graph linkages recorded in the COCI database.")

# Fetch events from MongoDB
@st.cache_data(ttl=60)
def fetch_statistics_data(mongo_uri, database_name):
    agg_client = pymongo.MongoClient(mongo_uri)
    agg_db = agg_client[database_name]
    
    events_cursor = agg_db["events"].find({}, {
        "_id": 1,
        "index": 1,
        "filenames": 1,
        "created_at": 1,
        "processed_at": 1,
        "processed": 1
    })
    return list(events_cursor)

raw_events = fetch_statistics_data(uri, db_name)

if not raw_events:
    st.info("ℹ️ No conferences found in the database yet. Add events to populate the analytics.")
    vis.render_footer()
    st.stop()

# Process data for analytics
total_events = len(raw_events)
organisers_dict = {}
year_counter = Counter()
country_counter = Counter()
affiliation_counter = Counter()
series_counter = Counter()
topics_counter = Counter()
external_links = {"DBLP": 0, "AIDA": 0, "ConfIDent": 0}
verified_orgs_count = 0
total_org_assignments = 0

for doc in raw_events:
    processed = doc.get("processed", {})
    
    # Year
    year = str(processed.get("year", "")).strip()
    if year:
        year_counter[year] += 1
    else:
        year_counter["Unknown"] += 1
        
    # Series
    series = str(processed.get("conference_series", "")).strip()
    if series:
        series_counter[series] += 1
        
    # External dataset matches
    if processed.get("DBLP", {}).get("name") or processed.get("DBLP", {}).get("id"):
        external_links["DBLP"] += 1
    if processed.get("AIDA", {}).get("name") or processed.get("AIDA", {}).get("id"):
        external_links["AIDA"] += 1
    if processed.get("ConfIDent", {}).get("name") or processed.get("ConfIDent", {}).get("id"):
        external_links["ConfIDent"] += 1
        
    # Organisers
    for org in processed.get("organisers", []):
        total_org_assignments += 1
        name = str(org.get("organiser_name", "")).strip()
        if not name:
            continue
        
        orcid = str(org.get("orcid", "")).strip()
        openalex = str(org.get("openalex_page", "")).strip()
        is_verified = bool(org.get("verified", False))
        
        if is_verified:
            verified_orgs_count += 1
            
        key = orcid or openalex or name.lower()
        if key not in organisers_dict:
            organisers_dict[key] = {
                "name": name,
                "country": str(org.get("organiser_country", "")).strip(),
                "affiliation": str(org.get("organiser_affiliation", "")).strip(),
                "orcid": orcid,
                "openalex": openalex,
                "verified": is_verified,
                "events_count": 1
            }
        else:
            organisers_dict[key]["events_count"] += 1
            if is_verified:
                organisers_dict[key]["verified"] = True
                
        # Country
        country = str(org.get("organiser_country", "")).strip()
        if country:
            country_counter[country] += 1
            
        # Affiliation
        aff = str(org.get("organiser_affiliation", "")).strip()
        if aff:
            affiliation_counter[aff] += 1

    # Topics
    for t in processed.get("topics", []):
        t_clean = str(t).strip()
        if t_clean:
            topics_counter[t_clean] += 1

total_unique_organisers = len(organisers_dict)
unique_series = len(series_counter)

# ----------------- TOP METRIC CARDS -----------------
st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
m_col1, m_col2, m_col3, m_col4 = st.columns(4)

with m_col1:
    st.metric(label="Total Conferences", value=total_events, help="Total unique conference events stored in MongoDB")
with m_col2:
    st.metric(label="Unique Organisers", value=total_unique_organisers, help="Distinct scholars identified across all tracks")
with m_col3:
    st.metric(label="Conference Series", value=unique_series, help="Identified recurring academic series")
with m_col4:
    st.metric(label="Total Roles Assigned", value=total_org_assignments, help="Total track chair and committee roles indexed")

st.divider()

# ----------------- SECTION 1: EVENTS PER YEAR & SERIES -----------------
col_chart_year, col_chart_series = st.columns([1, 1])

with col_chart_year:
    st.markdown("#### 📅 Events per Year")
    sorted_years = sorted(
        [y for y in year_counter.keys() if y != "Unknown"],
        key=lambda x: int(x) if x.isdigit() else 0
    )
    if "Unknown" in year_counter:
        sorted_years.append("Unknown")
        
    year_df = pd.DataFrame({
        "Year": sorted_years,
        "Conferences": [year_counter[y] for y in sorted_years]
    }).set_index("Year")
    
    st.bar_chart(year_df, color="#183642", height=320)

with col_chart_series:
    st.markdown("#### 🏛️ Top Conference Series")
    if series_counter:
        top_series = series_counter.most_common(8)
        series_df = pd.DataFrame(top_series, columns=["Conference Series", "Conferences"]).set_index("Conference Series")
        st.bar_chart(series_df, color="#1e6b60", height=320)
    else:
        st.info("No conference series identified yet.")

st.divider()

# ----------------- SECTION 2: ORGANISERS & GEOGRAPHIC DISTRIBUTION -----------------
col_orgs, col_geo = st.columns([1, 1])

with col_orgs:
    st.markdown("#### 👥 Most Frequent Organisers")
    sorted_orgs = sorted(organisers_dict.values(), key=lambda x: x["events_count"], reverse=True)[:10]
    org_table_data = []
    for o in sorted_orgs:
        org_table_data.append({
            "Organiser": o["name"],
            "Affiliation": o["affiliation"] or "-",
            "Country": o["country"] or "-",
            "Events Organised": o["events_count"],
            "Verified": "✅" if o["verified"] else "⏳"
        })
    st.dataframe(pd.DataFrame(org_table_data), use_container_width=True, hide_index=True)

with col_geo:
    st.markdown("#### 🌍 Top Organiser Countries")
    if country_counter:
        top_countries = country_counter.most_common(10)
        country_df = pd.DataFrame(top_countries, columns=["Country", "Count"]).set_index("Country")
        st.bar_chart(country_df, color="#b37424", height=320)
    else:
        st.info("No country affiliations recorded yet.")

st.divider()

# ----------------- SECTION 3: TOPICS & LINKED OPEN DATA INTEGRATION -----------------
col_topics, col_links = st.columns([1, 1])

with col_topics:
    st.markdown("#### 🏷️ Common Tracks & Topic Keywords")
    if topics_counter:
        top_topics = topics_counter.most_common(10)
        topic_df = pd.DataFrame(top_topics, columns=["Topic / Track", "Occurrences"])
        st.dataframe(topic_df, use_container_width=True, hide_index=True)
    else:
        st.info("No topic metadata recorded.")

with col_links:
    st.markdown("#### 🔗 Linked Dataset Matching Coverage")
    st.caption("Conferences linked to established academic dataset registries.")
    
    link_df = pd.DataFrame({
        "Dataset": ["DBLP", "AIDA Dashboard", "ConfIDent"],
        "Matched Events": [external_links["DBLP"], external_links["AIDA"], external_links["ConfIDent"]],
        "Coverage (%)": [
            f"{(external_links['DBLP'] / total_events * 100):.1f}%",
            f"{(external_links['AIDA'] / total_events * 100):.1f}%",
            f"{(external_links['ConfIDent'] / total_events * 100):.1f}%"
        ]
    })
    st.dataframe(link_df, use_container_width=True, hide_index=True)

st.markdown("<div style='height: 30px;'></div>", unsafe_allow_html=True)
vis.render_footer()
