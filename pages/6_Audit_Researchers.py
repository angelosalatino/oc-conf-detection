#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
os.environ['FAISS_OPT_LEVEL'] = ''  # do this BEFORE importing any faiss library

import streamlit as st
import configparser
import requests
import pyalex
from pyalex import Authors, Works

from classes.visualiser import ConferenceVisualiser

# Ensure configuration is loaded
if 'config' not in st.session_state:
    st.session_state['config'] = configparser.ConfigParser()
    st.session_state['config'].read('config.ini')

config = st.session_state['config']
vis = ConferenceVisualiser()

# Page configuration
st.set_page_config(
    layout="wide",
    page_title=f"Audit Researcher - {config['APP']['app_acronym']}",
    page_icon="🌐",
)

# Load CSS styles
vis.local('assets/css/bootstrap.min.css')
vis.local('assets/css/mycss.css')

with st.sidebar:
    vis.add_logo()

# Handle selection states
if 'selected_openalex_author' not in st.session_state:
    st.session_state['selected_openalex_author'] = None

# ----------------- SEARCH & PROFILE SELECT VIEW -----------------
if st.session_state['selected_openalex_author'] is None:
    st.markdown("<div id='top' style='height: 40px;'></div>", unsafe_allow_html=True)
    st.title("Audit Researcher")
    st.markdown("Search for an academic profile on OpenAlex to retrieve their publications and audit them against the RetractionWatch database and PubPeer comments.")

    # Search panel
    col1, col2, col3 = st.columns([1, 3, 1])
    with col2:
        query_name = st.text_input("Search researcher by name", placeholder="e.g. Didier Raoult...", label_visibility="collapsed")
        search_clicked = st.button("Search OpenAlex", use_container_width=True, type="primary")

    if 'openalex_search_query' not in st.session_state:
        st.session_state['openalex_search_query'] = ''

    if search_clicked:
        st.session_state['openalex_search_query'] = query_name.strip()

    search_term = st.session_state.get('openalex_search_query', '').strip()
    if search_term:
        # Load API keys and query OpenAlex
        pyalex.config.api_key = config.get('OPENALEX', 'openalex_api', fallback='')
        
        try:
            with st.spinner("Searching OpenAlex researcher profiles..."):
                auths = Authors().search(search_term).get()
                
            if not auths:
                st.info("No matching researcher profiles found on OpenAlex.")
            else:
                st.subheader(f"Matching OpenAlex Profiles ({len(auths)})")
                for idx, author in enumerate(auths):
                    author_id = author.get("id")
                    name = author.get("display_name", "Unknown Researcher")
                    orcid = author.get("orcid") or ""
                    works_count = author.get("works_count", 0)
                    cited_by = author.get("cited_by_count", 0)
                    
                    last_inst = author.get("last_known_institution")
                    inst_name = last_inst.get("display_name", "") if last_inst else ""
                    country = last_inst.get("country_code", "") if last_inst else ""
                    
                    with st.container(border=True):
                        info_col, btn_col = st.columns([5, 1], vertical_alignment="center")
                        with info_col:
                            st.markdown(f"#### {name}")
                            if inst_name:
                                loc = f" ({country})" if country else ""
                                st.markdown(f"🏢 **Last Known Institution**: {inst_name}{loc}")
                            orcid_text = f"[{orcid}]({orcid})" if orcid else "*Not available*"
                            st.markdown(f"🔗 **ORCID**: {orcid_text} | 📚 **Papers**: {works_count} | 💬 **Citations**: {cited_by}")
                        with btn_col:
                            if st.button("Select Profile", key=f"sel_author_{idx}", type="primary", use_container_width=True):
                                st.session_state['selected_openalex_author'] = author
                                st.rerun()
        except Exception as e:
            st.error(f"❌ Failed to query OpenAlex: {e}")

# ----------------- AUDIT & CHECKS VIEW -----------------
else:
    author = st.session_state['selected_openalex_author']
    author_id = author.get("id")
    author_name = author.get("display_name", "Unknown Name")
    orcid = author.get("orcid") or ""
    
    if st.button("← Back to search results", type="secondary"):
        st.session_state['selected_openalex_author'] = None
        st.rerun()
        
    st.divider()
    st.title(f"👤 Researcher Audit: {author_name}")
    
    # Institution details
    last_inst = author.get("last_known_institution")
    inst_name = last_inst.get("display_name", "") if last_inst else ""
    country = last_inst.get("country_code", "") if last_inst else ""
    if inst_name:
        loc_str = f" ({country})" if country else ""
        st.markdown(f"🏢 **Institution**: {inst_name}{loc_str}")
        
    # Metrics
    col_metrics = st.columns(3)
    with col_metrics[0]:
        st.metric("Total Papers", author.get("works_count", 0))
    with col_metrics[1]:
        st.metric("Total Citations", author.get("cited_by_count", 0))
    with col_metrics[2]:
        orcid_url = orcid if orcid.startswith("http") else f"https://orcid.org/{orcid}" if orcid else ""
        if orcid_url:
            st.markdown(f"🔗 **ORCID**: [{orcid}]({orcid_url})")
        st.markdown(f"🌐 [OpenAlex Profile Page]({author_id})")
        
    # Fetch works
    pyalex.config.api_key = config.get('OPENALEX', 'openalex_api', fallback='')
    
    with st.spinner("Retrieving publications from OpenAlex..."):
        try:
            # Use paginate() to get all publications by scrolling through pages
            works = []
            pager = Works().filter(author={"id": author_id}).paginate(n_max=None)
            for page in pager:
                works.extend(page)
        except Exception as e:
            st.error(f"❌ Failed to fetch publications from OpenAlex: {e}")
            vis.render_footer()
            st.stop()
            
    st.subheader(f"Auditing {len(works)} publications...")
    
    # ---------------- 1. RetractionWatch Database Audit ----------------
    st.markdown("### 🚨 RetractionWatch Database Audit")
    
    retracted_papers = []
    # Check works inside OpenAlex
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
            
    # Check Crossref retraction updates by name or orcid
    crossref_retracted = []
    crossref_url = "https://api.crossref.org/v1/works"
    params = {
        "query.author": author_name,
        "filter": "update-type:retraction",
        "rows": 50
    }
    if orcid:
        orcid_id = orcid.split("orcid.org/")[-1].strip()
        params["filter"] = f"orcid:{orcid_id},update-type:retraction"
        
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
                
                # Check for duplicates
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
    
    # ---------------- 2. PubPeer Comments Check ----------------
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
            # Query PubPeer POST API in batch mode
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

vis.render_footer()
