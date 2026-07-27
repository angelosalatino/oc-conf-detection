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

check_page_change("how_to_use")

st.set_page_config(
    layout="wide",
    page_title=f"How to use {config['APP']['app_acronym']}",
    page_icon="🌐",
)

# Load styles
vis.local('assets/css/bootstrap.min.css')
vis.local('assets/css/mycss.css')

with st.sidebar:
    vis.add_logo()

st.markdown("<div id='top' style='height: 40px;'></div>", unsafe_allow_html=True)
st.title(f"How to Use {config['APP']['app_acronym']}")
st.markdown(
    f"Welcome to the user guide for the **{config['APP']['app_name']}** portal. "
    f"This guide contains step-by-step instructions on how to use the different sections of the application."
)

st.divider()

# Table of Contents
st.markdown("### Table of Contents")
st.markdown(
    """
    * [1. Getting Started: The Hub Landing Page](#getting-started-the-hub-landing-page)
    * [2. Process Events](#process-events)
    * [3. Explore Events](#explore-events)
    * [4. Explore Organisers](#explore-organisers)
    * [5. Audit Researcher](#audit-researcher)
    """,
    unsafe_allow_html=True
)

st.divider()

# Section 1
st.subheader("1. Getting Started: The Hub Landing Page", anchor="getting-started-the-hub-landing-page")
st.markdown(
    f"When you launch the {config['APP']['app_acronym']} application, you are presented with a central landing page. "
    f"This page displays navigation cards pointing to the four primary features of the platform. "
    f"You can click on any card to navigate directly to that section. "
    f"Alternatively, you can navigate using the left sidebar. "
    f"To ensure a clean workspace, switching pages will automatically clear active search queries and selection states from other tools."
)

st.write("")

# Section 2
st.subheader("2. Process Events", anchor="process-events")
st.markdown(
    "The **Process Events** tool allows you to upload a conference's Call for Papers (CFP) to automatically extract metadata, topics, and organizer details.\n\n"
    "1. **Prepare the text file**: Locate the official Call for Papers text on the conference website. Copy the text, paste it into a blank text editor, and save it as a plain `.txt` file. Word documents and PDFs are not supported.\n"
    "2. **Upload the file**: Drag and drop or browse to select your `.txt` file using the centered uploader box.\n"
    "3. **Choose Processing Mode**:\n"
    "   * *Cached*: Retrieves previous results from the database if this exact file name has been processed before.\n"
    "   * *Mild Force*: Reuses the extracted metadata from LLM output but reruns local database matching and mapping logic.\n"
    "   * *Force*: Reprocesses the entire text file from scratch through the LLM orchestrator.\n"
    "4. **Analyze Results**: Click **Process**. Once completed, check the **Results** tab for structured conference details, organized tracks, topics, and matched organizers. Use the **Read Call for Papers** tab to view the formatted original text."
)

st.write("")

# Section 3
st.subheader("3. Explore Events", anchor="explore-events")
st.markdown(
    "The **Explore Events** tool enables you to search and browse through all processed conferences stored in the database.\n\n"
    "1. **Fuzzy Search**: Type keywords into the search bar. The tool searches across conference names, acronyms, series, and extracted topic lists.\n"
    "2. **Strict Relevance Filtering**: The system filters search results to exclude any match with a similarity score below **60%**.\n"
    "3. **Matched Topics**: If a search term matches an extracted topic of a conference, a lightbulb icon will highlight the matched topic (e.g. `Matched topic: 'Ontology Engineering'`).\n"
    "4. **Quick Browse**: Click the **I'm feeling lucky** button to quickly display the last 10 conferences added to the system.\n"
    "5. **View Event**: Click on any result card to view the complete parsed details of the conference."
)

st.write("")

# Section 4
st.subheader("4. Explore Organisers", anchor="explore-organisers")
st.markdown(
    "The **Explore Organisers** page compiles unique organizer records across all stored conferences.\n\n"
    "1. **Organizer Search**: Enter an organizer's name or affiliation. Results are filtered using a **60% minimum similarity match**.\n"
    "2. **Quick Browse**: Click **I'm feeling lucky** to display the 10 most recently added organizers.\n"
    "3. **Detailed Profiles**: Click **View Events** on any organizer card to view their profile, including verified affiliations, country codes, ORCID profile link, OpenAlex page, and a list of all conferences in the database they have organized."
)

st.write("")

# Section 5
st.subheader("5. Audit Researcher", anchor="audit-researcher")
st.markdown(
    "The **Audit Researcher** tool verifies publication integrity by checking researcher profiles against RetractionWatch and PubPeer.\n\n"
    "1. **Search Profiles**: Enter a researcher's name to query academic profiles on OpenAlex. Select the correct profile from the results list.\n"
    "2. **Fetch Publications**: The tool queries OpenAlex and downloads the researcher's complete publication record using cursor pagination.\n"
    "3. **RetractionWatch Check**: Scans the publication list for retracted articles. This uses OpenAlex's retraction status and queries the Crossref update API for retraction records matching the researcher's name or ORCID.\n"
    "4. **PubPeer Discussion Check**: Extracts DOIs from the publication list and queries the PubPeer API in batch. It displays any publications with comments, providing commenters lists and direct links to read discussions on PubPeer."
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
