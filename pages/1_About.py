#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import streamlit as st
from classes.visualiser import CoreVisualiser

if 'config' not in st.session_state:
    st.switch_page("COCI.py")

config = st.session_state['config']
vis = CoreVisualiser()

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

check_page_change("about")

st.set_page_config(
    layout="wide",
    page_title=f"About {config['APP']['app_acronym']}",
    page_icon="🌐",
)

# Load styles
vis.local('assets/css/bootstrap.min.css')
vis.local('assets/css/mycss.css')

with st.sidebar:
    vis.add_logo()

st.markdown("<div id='top' style='height: 40px;'></div>", unsafe_allow_html=True)
st.title(f"About the {config['APP']['app_name']}")
st.markdown(
    f"The **{config['APP']['app_name']}** is an AI-powered system designed to automate the extraction, "
    f"enrichment, search, and audit of scholarly conference metadata and academic organizer records."
)

st.divider()

# Table of Contents
st.markdown("### Table of Contents")
st.markdown(
    """
    * [1. Processing Modes](#processing-modes)
    * [2. Key Data Extracted](#key-data-extracted)
    * [3. Topic Extraction and FAISS Matching](#topic-extraction-and-faiss-matching)
    * [4. Organiser Matching and Verification](#organiser-matching-and-verification)
    * [5. Database Storage and Parallel Call for Papers](#database-storage-and-parallel-call-for-papers)
    * [6. Search and Exploration Pipelines](#search-and-exploration-pipelines)
    * [7. Researcher Auditing Integrations](#researcher-auditing-integrations)
    * [8. Rebranding COCI](#rebranding-coci)
    * [9. The Team](#the-team)
    """,
    unsafe_allow_html=True
)

st.divider()

# Section 1
st.subheader("1. Processing Modes", anchor="processing-modes")
st.markdown(
    "To optimize processing speed and control API resource utilization, the system offers three execution modes when parsing a document:\n\n"
    "* **Cached**: Instantly loads the fully matched and finalized JSON data from the database or local storage cache if the file was processed previously.\n"
    "* **Mild Force**: Reuses the LLM metadata extraction from the cache, but forces a clean execution of local semantic vector search pipelines and database matching algorithms to fetch updated database links.\n"
    "* **Force**: Bypasses all cache systems, initiating a fresh LLM extraction and top-to-bottom re-processing of the document."
)

st.write("")

# Section 2
st.subheader("2. Key Data Extracted", anchor="key-data-extracted")
st.markdown(
    "The system extracts the following structured elements from Call for Papers texts:\n\n"
    "* **Event Name**: Full title of the conference or workshop.\n"
    "* **Conference Series**: Normalized name of the recurring conference series.\n"
    "* **Event Acronym**: The official acronym for the event.\n"
    "* **Colocated With**: Details of any co-hosted or parent conferences.\n"
    "* **Year**: Calendar year of the conference.\n"
    "* **Location**: Scheduled city and country.\n"
    "* **Organisers**: Structured list of organizing committee members, including their affiliations, countries, and roles/tracks."
)

st.write("")

# Section 3
st.subheader("3. Topic Extraction and FAISS Matching", anchor="topic-extraction-and-faiss-matching")
st.markdown(
    "Standardizing extracted topics of interest is key to categorizing events:\n\n"
    "1. **Raw Extraction**: Extracted topics are retrieved directly from the text.\n"
    "2. **Vector Embedding**: Raw topics are encoded into high-dimensional semantic vectors using a SentenceTransformer model.\n"
    "3. **Similarity Indexing**: Vectors query a local FAISS index containing standardized OpenAlex topics.\n"
    "4. **Interactive Filtering**: The interface includes a similarity threshold slider. Users can dynamically filter mapped topics on the fly, with zero-lag recalculation, and persist their custom threshold choice to the database."
)

st.write("")

# Section 4
st.subheader("4. Organiser Matching and Verification", anchor="organiser-matching-and-verification")
st.markdown(
    "Matches extracted organizer names against OpenAlex to identify verified academic records:\n\n"
    "1. **Quality Check**: Discards homogeneous/default affiliations to avoid false matches.\n"
    "2. **Profile Mapping**: Attempts to map names to profiles within their stated institution. If unsuccessful, runs a name-based fallback search.\n"
    "3. **Affiliation Verification**: Cross-references stated affiliations with recent publication history. Validated matches are marked with a verification symbol (✪).\n"
    "4. **Identifier Extraction**: Retrieves ORCID and ROR identifiers to links profiles to global registries."
)

st.write("")

# Section 5
st.subheader("5. Database Storage and Parallel Call for Papers", anchor="database-storage-and-parallel-call-for-papers")
st.markdown(
    "All processed events are stored in a MongoDB collection. To capture the full context of a conference:\n\n"
    "* **Parallel Arrays**: Stored documents save the raw Call for Papers texts in a parallel `cfps` array synchronized 1-to-1 with file names.\n"
    "* **Multiple CFPs**: If a conference has multiple Calls for Papers associated with it (e.g. from different tracks or update cycles), the second text is added to the MongoDB list, preserving all sources for search and reading."
)

st.write("")

# Section 6
st.subheader("6. Search and Exploration Pipelines", anchor="search-and-exploration-pipelines")
st.markdown(
    "The search interface supports multi-level exploration of database records:\n\n"
    "* **Event Search**: Matches user queries against event names, acronyms, series, and standard OpenAlex topics, highlighting topic matches with lightbulb badges.\n"
    "* **Organiser Aggregation**: Aggregates unique organizer profiles across the database using ORCIDs, OpenAlex IDs, and normalized names, linking each organizer to their total list of contributed conferences.\n"
    "* **Match Constraints**: Searches enforce a strict **60% minimum similarity threshold** to filter out irrelevant results."
)

st.write("")

# Section 7
st.subheader("7. Researcher Auditing Integrations", anchor="researcher-auditing-integrations")
st.markdown(
    "The portal incorporates integrity checks to audit researcher publication lists:\n\n"
    "* **Publications Fetch**: Retrieves the complete publication list of a selected author from OpenAlex using cursor-based pagination.\n"
    "* **Retraction Watch Checks**: Cross-references DOIs against retraction registries. This utilizes OpenAlex's retraction updates and makes real-time calls to the Crossref API using `update-type:retraction` and ORCID filters.\n"
    "* **PubPeer Checks**: Gathers DOIs and queries the PubPeer publications API via batch POST requests, displaying commenter lists and direct links to post-publication discussions."
)

st.write("")

# Section 8
st.subheader("8. Rebranding COCI", anchor="rebranding-coci")
st.markdown(
    "By shifting the definition of the acronym COCI from \"Conference Organising Committee Identifier\" to "
    "**\"Conference Organisers and Content Identifier\"**, the focus has been broadened from identifying committee members "
    "to capturing a complete snapshot of the event's scientific topics, tracks, and metadata, while preserving the established branding."
)

st.write("")

# Section 9
st.subheader("9. The Team", anchor="the-team")
st.markdown(
    f"This portal is developed by the **Knowledge Media Institute** of the **Open University** in collaboration with **Springer Nature**.\n\n"
    f"For questions or info, contact **Angelo Salatino** (angelo.salatino at open.ac.uk)."
)

# Scroll to top button
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
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        z-index: 999999;
        transition: transform 0.2s;
    " onmouseover="this.style.transform='scale(1.1)'" onmouseout="this.style.transform='scale(1)'">↑</a>
    """,
    unsafe_allow_html=True
)

st.write("")
vis.render_footer()