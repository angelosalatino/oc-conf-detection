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
    page_title=f"How to use {config['APP']['app_acronym']}",
    page_icon="🌐",
)

### WEBAPP
vis.local('assets/css/bootstrap.min.css')
vis.local('assets/css/mycss.css')

with st.sidebar:
    vis.add_logo()

st.markdown(
    f"""
    <div id="top" style="height: 60px;"></div>
    
    # How to Use {config['APP']['app_acronym']}
    
    Using {config['APP']['app_acronym']} is a straightforward process based entirely on text-file inputs. Because the system parses information directly from plain text, users simply need to compile the conference data manually. To do this, create a standard .txt file and paste the complete text from the online Call for Papers (CFP). For the most accurate and comprehensive analysis, ensure the file includes key details such as the event's location, dates, description, chairs, and organizers, as well as session schedules if they are available. Once the .txt file is prepared, it can be submitted directly to the platform for processing.
    
    # Step-by-Step Guidelines
    
    1. **Gather the conference data** (Source material)
       
       Locate the official Call for Papers (CFP) on the conference website.
       
    2. **Prepare the text file** (.txt format only)
       
       Create a new plain text file (.txt). {config['APP']['app_acronym']} processes text files exclusively, so do not use Word documents or PDFs.
       
    3. **Extract and paste information** (Include key metadata)
       
       Copy and paste all relevant information from the website into your text file. For best results, include the event description, location, dates, lists of chairs/organizers, and any available session details.
       
    4. **Submit to {config['APP']['app_acronym']}** (Parsing phase)
       
       Upload or submit your prepared .txt file to the {config['APP']['app_acronym']} platform to initiate the unsupervised parsing and analysis.
       
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
