#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
os.environ['FAISS_OPT_LEVEL'] = ''  # do this BEFORE importing any faiss library

import streamlit as st
import configparser
import pymongo
from rapidfuzz import fuzz
from pathlib import Path
import requests
import pyalex
from pyalex import Authors, Works

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

check_page_change("search_organiser")

# Page configuration
st.set_page_config(
    layout="wide",
    page_title=f"Search Organiser - {config['APP']['app_acronym']}",
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
    st.warning("⚠️ The **Search Organiser** page requires MongoDB to be active. Please enable it by setting `type = mongodb` or `type = both` in the `[STORAGE]` section of your `config.ini` file.")
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


# Caching the unique organisers aggregation across all events
@st.cache_data(ttl=60)
def get_all_organisers(mongo_uri, database_name):
    agg_client = pymongo.MongoClient(mongo_uri)
    agg_db = agg_client[database_name]
    
    events_list = list(agg_db["events"].find({}, {
        "_id": 1,
        "index": 1,
        "processed.event_name": 1,
        "processed.event_acronym": 1,
        "processed.conference_series": 1,
        "processed.year": 1,
        "processed.organisers": 1
    }))
    
    organisers_map = {}
    for doc in events_list:
        processed = doc.get("processed", {})
        event_info = {
            "index": doc.get("index") or doc.get("_id"),
            "event_name": processed.get("event_name", ""),
            "event_acronym": processed.get("event_acronym", ""),
            "conference_series": processed.get("conference_series", ""),
            "year": processed.get("year", "")
        }
        
        for org in processed.get("organisers", []):
            name = org.get("organiser_name", "").strip()
            if not name:
                continue
                
            orcid = org.get("orcid", "")
            openalex = org.get("openalex_page", "")
            
            # Unique key combining ORCID, OpenAlex, or lowercase name
            key = orcid or openalex or name.lower()
            
            if key not in organisers_map:
                organisers_map[key] = {
                    "key": key,
                    "name": name,
                    "openalex_name": org.get("openalex_name", ""),
                    "affiliation": org.get("organiser_affiliation", ""),
                    "orcid": orcid,
                    "openalex_page": openalex,
                    "affiliation_ror": org.get("affiliation_ror", ""),
                    "country": org.get("organiser_country", ""),
                    "events": [event_info]
                }
            else:
                entry = organisers_map[key]
                # Avoid duplicates in organised events list
                if not any(e["index"] == event_info["index"] for e in entry["events"]):
                    entry["events"].append(event_info)
                    
                # Merge profile details if they were previously missing
                for field in ["openalex_name", "affiliation", "orcid", "openalex_page", "affiliation_ror", "country"]:
                    if not entry.get(field) and org.get(field):
                        entry[field] = org.get(field)
                        
    return list(organisers_map.values())


# ----------------- LEVEL 1: EVENT DETAILS VIEW -----------------
if 'selected_event_id' in st.session_state:
    selected_id = st.session_state['selected_event_id']
    event_doc = db["events"].find_one({"_id": selected_id})
    
    if not event_doc:
        st.error(f"Event with ID {selected_id} not found in the database.")
        if st.button("← Back"):
            del st.session_state['selected_event_id']
            st.rerun()
    else:
        # Determine appropriate back routing
        back_label = "← Back to organiser profile" if 'selected_organiser_key' in st.session_state else "← Back to search results"
        if st.button(back_label, type="secondary"):
            del st.session_state['selected_event_id']
            st.rerun()
            
        st.divider()
        conf = Conference.from_dict(event_doc.get("processed", {}))
        dest_folder = config.get('FOLDERS', 'destination_folder', fallback='processed_cfps')
        storage = ConferenceStorage(dest_folder)
        filenames = event_doc.get("filenames", [])
        filename = filenames[0] if filenames else f"event_{selected_id}"
        
        # Check if Call for Papers text is stored in the DB
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

# ----------------- LEVEL 2: ORGANISER PROFILE VIEW -----------------
elif 'selected_organiser_key' in st.session_state:
    org_key = st.session_state['selected_organiser_key']
    organisers_list = get_all_organisers(uri, db_name)
    org = next((o for o in organisers_list if o["key"] == org_key), None)
    
    if not org:
        st.error("Organiser profile not found.")
        if st.button("← Back to search results"):
            del st.session_state['selected_organiser_key']
            st.rerun()
    else:
        if st.button("← Back to search results", type="secondary"):
            del st.session_state['selected_organiser_key']
            st.rerun()
            
        st.divider()
        st.title(f"👤 {org['name']}")
        
        if org.get("openalex_name") and org["openalex_name"].lower() != org["name"].lower():
            st.markdown(f"**OpenAlex Name**: {org['openalex_name']}")
            
        aff = org.get("affiliation", "")
        country = org.get("country", "")
        if aff:
            st.markdown(f"🏢 **Affiliation**: {aff}")
        if country:
            st.markdown(f"📍 **Country**: {country}")
            
        st.markdown("### 🔗 Identifiers")
        col_ids = st.columns(2)
        with col_ids[0]:
            orcid = org.get("orcid", "")
            if orcid:
                orcid_url = orcid if orcid.startswith("http") else f"https://orcid.org/{orcid}"
                st.markdown(f"**ORCID**: [{orcid}]({orcid_url})")
            else:
                st.markdown("**ORCID**: *Not available*")
        with col_ids[1]:
            openalex_url = org.get("openalex_page", "")
            if openalex_url:
                st.markdown(f"**OpenAlex Profile**: [OpenAlex Link]({openalex_url})")
            else:
                st.markdown("**OpenAlex Profile**: *Not available*")
                
        st.divider()
        
        tab_events, tab_audit = st.tabs(["📚 Organised Events", "🔍 Researcher Audit"])
        
        with tab_events:
            st.subheader("📚 Organised Events")
            st.write(f"This organiser has contributed to {len(org['events'])} event(s) in the database:")
            
            for ev in org["events"]:
                ev_idx = ev["index"]
                ev_name = ev.get("event_name", "Unknown Event")
                ev_year = ev.get("year", "")
                ev_series = ev.get("conference_series", "")
                
                with st.container(border=True):
                    ev_col, btn_col = st.columns([5, 1], vertical_alignment="center")
                    with ev_col:
                        st.markdown(f"#### {ev_name} ({ev_year})")
                        if ev_series and ev_series != ev_name:
                            st.markdown(f"**Series**: {ev_series}")
                        st.markdown(f"**ID / Index**: {ev_idx}")
                    with btn_col:
                        if st.button("View Event", key=f"org_view_ev_{ev_idx}", type="primary", use_container_width=True):
                            st.session_state['selected_event_id'] = ev_idx
                            st.rerun()

        with tab_audit:
            st.subheader("🔍 Researcher Audit")
            openalex_page = org.get("openalex_page", "")
            
            if not openalex_page:
                st.info("⚠️ No OpenAlex profile is linked to this organiser, so an automatic audit cannot be performed.")
            else:
                # Configure OpenAlex API
                pyalex.config.api_key = config.get('OPENALEX', 'openalex_api', fallback='')
                author_id = openalex_page.strip()
                
                try:
                    with st.spinner("Retrieving profile and publications from OpenAlex..."):
                        author_obj = Authors()[author_id]
                        works = []
                        pager = Works().filter(author={"id": author_id}).paginate(n_max=None)
                        for page in pager:
                            works.extend(page)
                            
                    # Profile summary & metrics
                    audit_author_name = author_obj.get("display_name", org.get("openalex_name") or org.get("name"))
                    audit_orcid = author_obj.get("orcid") or org.get("orcid") or ""
                    
                    last_inst = author_obj.get("last_known_institution")
                    inst_name = last_inst.get("display_name", "") if last_inst else ""
                    inst_country = last_inst.get("country_code", "") if last_inst else ""
                    if inst_name:
                        loc_str = f" ({inst_country})" if inst_country else ""
                        st.markdown(f"🏢 **Last Known Institution**: {inst_name}{loc_str}")
                        
                    total_profile_works = author_obj.get("works_count", len(works))
                    col_m1, col_m2, col_m3 = st.columns(3)
                    with col_m1:
                        st.metric(
                            "Total Papers",
                            f"{len(works)}",
                            help=f"Audited {len(works)} core publication records (out of {total_profile_works} total profile records across all repositories and expansion items)."
                        )
                    with col_m2:
                        st.metric("Total Citations", author_obj.get("cited_by_count", 0))
                    with col_m3:
                        if audit_orcid:
                            audit_orcid_url = audit_orcid if audit_orcid.startswith("http") else f"https://orcid.org/{audit_orcid}"
                            st.markdown(f"🔗 **ORCID**: [{audit_orcid}]({audit_orcid_url})")
                        st.markdown(f"🌐 [OpenAlex Profile Page]({author_id})")
                        
                    st.divider()
                    st.write(f"Auditing **{len(works)}** publications...")
                    if total_profile_works > len(works):
                        st.caption(f"ℹ️ Auditing all **{len(works)}** indexed core publications. (OpenAlex reports **{total_profile_works}** total records, including unindexed repository items and expansion entries).")
                    
                    # 1. RetractionWatch Database Audit
                    st.markdown("### 🚨 RetractionWatch Database Audit")
                    
                    retracted_papers = []
                    for w in works:
                        if w.get("is_retracted"):
                            title = w.get("title", "Unknown Title")
                            doi = w.get("doi") or ""
                            if doi.startswith("https://doi.org/"):
                                doi = doi.replace("https://doi.org/", "")
                            pub_year = w.get("publication_year", "")
                            retracted_papers.append({
                                "title": title,
                                "doi": doi,
                                "year": pub_year,
                                "source": "OpenAlex (RetractionWatch)"
                            })
                            
                    # Crossref retraction updates check
                    crossref_retracted = []
                    crossref_url = "https://api.crossref.org/v1/works"
                    params = {
                        "query.author": audit_author_name,
                        "filter": "update-type:retraction",
                        "rows": 50
                    }
                    if audit_orcid:
                        orcid_num = audit_orcid.split("orcid.org/")[-1].strip()
                        params["filter"] = f"orcid:{orcid_num},update-type:retraction"
                        
                    try:
                        resp = requests.get(crossref_url, params=params, timeout=10)
                        if resp.status_code == 200:
                            items = resp.json().get("message", {}).get("items", [])
                            for item in items:
                                c_doi = item.get("DOI", "")
                                c_title = item.get("title", ["Unknown Title"])[0]
                                c_year = ""
                                date_parts = item.get("created", {}).get("date-parts", [[None]])[0]
                                if date_parts and date_parts[0]:
                                    c_year = date_parts[0]
                                
                                if not any(p["doi"].lower() == c_doi.lower() for p in retracted_papers):
                                    crossref_retracted.append({
                                        "title": c_title,
                                        "doi": c_doi,
                                        "year": c_year,
                                        "source": "Crossref Retractions"
                                    })
                    except Exception as e:
                        st.caption(f"Note: Crossref query bypassed or failed: {e}")
                        
                    all_retracted = retracted_papers + crossref_retracted
                    
                    if all_retracted:
                        st.error(f"⚠️ **FLAGGED**: Found {len(all_retracted)} retracted paper(s) associated with this researcher!")
                        for p in all_retracted:
                            with st.container(border=True):
                                st.markdown(f"❌ **{p['title']}** ({p['year']})")
                                if p['doi']:
                                    st.markdown(f"**DOI**: [{p['doi']}](https://doi.org/{p['doi']})")
                                st.markdown(f"**Verification Source**: {p['source']}")
                    else:
                        st.success("✅ **Passed**: No retracted papers found in RetractionWatch or Crossref databases.")
                        
                    st.divider()
                    
                    # 2. PubPeer Comments Check
                    st.markdown("### 💬 PubPeer Post-Publication Peer Review")
                    
                    dois = []
                    doi_to_work = {}
                    for w in works:
                        doi = w.get("doi") or ""
                        if doi:
                            if doi.startswith("https://doi.org/"):
                                doi = doi.replace("https://doi.org/", "")
                            doi = doi.strip()
                            dois.append(doi)
                            doi_to_work[doi] = w
                            
                    pubpeer_results = []
                    if dois:
                        pubpeer_url = "https://pubpeer.com/v3/publications"
                        try:
                            resp = requests.post(pubpeer_url, json={"dois": dois, "devkey": "Zotero"}, timeout=10)
                            if resp.status_code == 200:
                                feedbacks = resp.json().get("feedbacks", [])
                                for fb in feedbacks:
                                    doi_key = fb.get("id")
                                    matched_work = doi_to_work.get(doi_key, {})
                                    pubpeer_results.append({
                                        "title": fb.get("title") or matched_work.get("title") or "Unknown Title",
                                        "doi": doi_key,
                                        "total_comments": fb.get("total_comments", 0),
                                        "last_comment": fb.get("last_commented_at", ""),
                                        "url": fb.get("url", ""),
                                        "users": fb.get("users", "")
                                    })
                        except Exception as e:
                            st.warning(f"Could not check comments on PubPeer: {e}")
                            
                    if pubpeer_results:
                        st.warning(f"💡 **ALERT**: Found {len(pubpeer_results)} paper(s) with comments or discussions on PubPeer.")
                        for fb in pubpeer_results:
                            with st.container(border=True):
                                st.markdown(f"💬 **{fb['title']}**")
                                st.markdown(f"**Comments count**: {fb['total_comments']} | **Last commented**: {fb['last_comment']}")
                                if fb['users']:
                                    st.markdown(f"**Commenters**: *{fb['users']}*")
                                st.markdown(f"🔗 [Read comments on PubPeer]({fb['url']})")
                    else:
                        st.success("✅ **Passed**: No comments found on PubPeer for this author's papers.")
                        
                except Exception as e:
                    st.error(f"❌ Failed to run audit: {e}")

# ----------------- LEVEL 3: SEARCH LIST VIEW -----------------
else:
    st.markdown("<div id='top' style='height: 40px;'></div>", unsafe_allow_html=True)
    st.title("Search Organiser in COCI")
    st.markdown("Search for conference organisers by name, openalex name, or affiliation, or click **I'm feeling lucky** to see the latest organisers added to the system.")

    # Centered Search Controls
    col1, col2, col3 = st.columns([1, 3, 1])
    with col2:
        search_query = st.text_input("Search organisers", placeholder="e.g. Manolis Koubarakis...", label_visibility="collapsed")
        
        btn_col1, btn_col2 = st.columns([1, 1])
        with btn_col1:
            search_clicked = st.button("Search", use_container_width=True, type="primary")
        with btn_col2:
            lucky_clicked = st.button("I'm feeling lucky", use_container_width=True)

    if 'org_search_mode' not in st.session_state:
        st.session_state['org_search_mode'] = None
    if 'org_search_term' not in st.session_state:
        st.session_state['org_search_term'] = ''

    if search_clicked:
        st.session_state['org_search_mode'] = 'search'
        st.session_state['org_search_term'] = search_query.strip()
    elif lucky_clicked:
        st.session_state['org_search_mode'] = 'lucky'
        st.session_state['org_search_term'] = ''

    mode = st.session_state.get('org_search_mode')
    results = []
    
    all_orgs = get_all_organisers(uri, db_name)

    if mode == 'lucky':
        # Sort organisers by the highest event index they contributed to (descending) to represent the "latest" added
        all_orgs_sorted = list(all_orgs)
        all_orgs_sorted.sort(key=lambda x: max(e["index"] for e in x["events"]) if x["events"] else 0, reverse=True)
        results = all_orgs_sorted[:10]
        st.subheader("Last 10 organisers added to the system")
    elif mode == 'search':
        query = st.session_state.get('org_search_term', '').strip()
        if not query:
            st.warning("Please enter a query in the search box first.")
        else:
            matched = []
            for org in all_orgs:
                name = org.get("name", "")
                oa_name = org.get("openalex_name", "")
                aff = org.get("affiliation", "")
                
                # Check fuzzy matches
                name_score = fuzz.WRatio(query.lower(), name.lower())
                oa_name_score = fuzz.WRatio(query.lower(), oa_name.lower()) if oa_name else 0
                aff_score = fuzz.WRatio(query.lower(), aff.lower()) if aff else 0
                
                max_score = max(name_score, oa_name_score, aff_score)
                if max_score >= 60:  # 60% match score threshold
                    org["similarity"] = max_score
                    matched.append(org)
            
            # Sort by similarity score descending, and then by Name ascending
            matched.sort(key=lambda x: (x.get("similarity", 0), x.get("name", "").lower()), reverse=True)
            results = matched
            st.subheader(f"Search results for '{query}' ({len(results)} matches)")

    # Display list of organisers
    if mode == 'lucky' or (mode == 'search' and st.session_state.get('org_search_term', '').strip()):
        if not results:
            st.info("No matching organisers found in the database.")
        else:
            for org in results:
                key = org["key"]
                name = org["name"]
                aff = org.get("affiliation", "")
                country = org.get("country", "")
                ev_count = len(org["events"])
                
                similarity_badge = ""
                if "similarity" in org:
                    similarity_badge = f" :blue-badge[Match score: {org['similarity']:.1f}%]"

                with st.container(border=True):
                    info_col, btn_col = st.columns([5, 1], vertical_alignment="center")
                    with info_col:
                        st.markdown(f"#### {name}{similarity_badge}")
                        if aff:
                            loc_info = f" ({country})" if country else ""
                            st.markdown(f"🏢 **Affiliation**: {aff}{loc_info}")
                        st.markdown(f"📅 **Events Contributed**: {ev_count}")
                    with btn_col:
                        if st.button("View Events", key=f"org_btn_{key}", type="primary", use_container_width=True):
                            st.session_state['selected_organiser_key'] = key
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
