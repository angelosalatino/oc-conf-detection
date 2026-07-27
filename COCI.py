#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import streamlit as st
import configparser
from classes.visualiser import ConferenceVisualiser

def read_config_file():
    if 'config' not in st.session_state:
        st.session_state['config'] = configparser.ConfigParser()
        st.session_state['config'].read('config.ini')

def check_page_change(page_name):
    if 'current_page' not in st.session_state:
        st.session_state['current_page'] = page_name
    elif st.session_state['current_page'] != page_name:
        st.session_state['current_page'] = page_name
        keys_to_clear = [
            'selected_event_id', 'selected_organiser_key', 
            'search_mode', 'search_term', 
            'org_search_mode', 'org_search_term',
            'selected_openalex_author', 'openalex_search_query',
            'processed_conf', 'processed_filename', 'processed_cfp_text'
        ]
        for key in keys_to_clear:
            if key in st.session_state:
                del st.session_state[key]

def main():
    read_config_file()
    check_page_change("home")
    
    config = st.session_state['config']
    vis = ConferenceVisualiser()
    
    st.set_page_config(
        layout="wide",
        page_title=config['APP']['app_acronym'],
        page_icon="🌐"
    )
    
    vis.local('assets/css/bootstrap.min.css')
    vis.local('assets/css/mycss.css')
    
    with st.sidebar:
        vis.add_logo()
        
    st.title(config['APP']['app_name'])
    st.markdown(
        f"<h4 style='text-align: left; color: gray; margin-bottom: 40px; font-weight: normal; line-height: 1.5;'>"
        f"Welcome to the Conference Organisers and Content Identifier (COCI). "
        f"Select one of the tools below or use the sidebar navigation to get started."
        f"</h4>",
        unsafe_allow_html=True
    )
    
    # 2x2 Grid Layout for features with clickable HTML links
    row1_col1, row1_col2 = st.columns(2)
    with row1_col1:
        st.markdown(
            """
            <a href="Process_Events" target="_self" style="text-decoration: none; color: inherit;">
                <div style="border: 1px solid #e6e8eb; padding: 25px; border-radius: 12px; cursor: pointer; background: #ffffff; transition: all 0.3s ease; box-shadow: 0 2px 4px rgba(0,0,0,0.02); height: 180px;" 
                     onmouseover="this.style.transform='translateY(-4px)'; this.style.boxShadow='0 8px 16px rgba(0,0,0,0.06)'; this.style.borderColor='#183642';"
                     onmouseout="this.style.transform='none'; this.style.boxShadow='0 2px 4px rgba(0,0,0,0.02)'; this.style.borderColor='#e6e8eb';">
                  <h3 style="margin-top:0; color:#1a1d20; text-align:center;">Process Events</h3>
                  <p style="color:#5f6368; font-size:14.5px; line-height:1.6; margin-bottom:0;">
                    Upload a Call for Papers in text format to automatically extract and structure its conference details, organizers, and research topics using AI.
                  </p>
                </div>
            </a>
            """,
            unsafe_allow_html=True
        )
                
    with row1_col2:
        st.markdown(
            """
            <a href="Explore_Events" target="_self" style="text-decoration: none; color: inherit;">
                <div style="border: 1px solid #e6e8eb; padding: 25px; border-radius: 12px; cursor: pointer; background: #ffffff; transition: all 0.3s ease; box-shadow: 0 2px 4px rgba(0,0,0,0.02); height: 180px;" 
                     onmouseover="this.style.transform='translateY(-4px)'; this.style.boxShadow='0 8px 16px rgba(0,0,0,0.06)'; this.style.borderColor='#183642';"
                     onmouseout="this.style.transform='none'; this.style.boxShadow='0 2px 4px rgba(0,0,0,0.02)'; this.style.borderColor='#e6e8eb';">
                  <h3 style="margin-top:0; color:#1a1d20; text-align:center;">Explore Events</h3>
                  <p style="color:#5f6368; font-size:14.5px; line-height:1.6; margin-bottom:0;">
                    Search and inspect all processed conferences in the database by topic, acronym, name, or series, or browse the latest additions.
                  </p>
                </div>
            </a>
            """,
            unsafe_allow_html=True
        )
                
    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
    
    row2_col1, row2_col2 = st.columns(2)
    with row2_col1:
        st.markdown(
            """
            <a href="Explore_Organisers" target="_self" style="text-decoration: none; color: inherit;">
                <div style="border: 1px solid #e6e8eb; padding: 25px; border-radius: 12px; cursor: pointer; background: #ffffff; transition: all 0.3s ease; box-shadow: 0 2px 4px rgba(0,0,0,0.02); height: 180px;" 
                     onmouseover="this.style.transform='translateY(-4px)'; this.style.boxShadow='0 8px 16px rgba(0,0,0,0.06)'; this.style.borderColor='#183642';"
                     onmouseout="this.style.transform='none'; this.style.boxShadow='0 2px 4px rgba(0,0,0,0.02)'; this.style.borderColor='#e6e8eb';">
                  <h3 style="margin-top:0; color:#1a1d20; text-align:center;">Explore Organisers</h3>
                  <p style="color:#5f6368; font-size:14.5px; line-height:1.6; margin-bottom:0;">
                    Browse and search academic organizers who have contributed to stored conferences, inspect their profiles, and view their events.
                  </p>
                </div>
            </a>
            """,
            unsafe_allow_html=True
        )
                
    with row2_col2:
        st.markdown(
            """
            <a href="Audit_Researchers" target="_self" style="text-decoration: none; color: inherit;">
                <div style="border: 1px solid #e6e8eb; padding: 25px; border-radius: 12px; cursor: pointer; background: #ffffff; transition: all 0.3s ease; box-shadow: 0 2px 4px rgba(0,0,0,0.02); height: 180px;" 
                     onmouseover="this.style.transform='translateY(-4px)'; this.style.boxShadow='0 8px 16px rgba(0,0,0,0.06)'; this.style.borderColor='#183642';"
                     onmouseout="this.style.transform='none'; this.style.boxShadow='0 2px 4px rgba(0,0,0,0.02)'; this.style.borderColor='#e6e8eb';">
                  <h3 style="margin-top:0; color:#1a1d20; text-align:center;">Audit Researcher</h3>
                  <p style="color:#5f6368; font-size:14.5px; line-height:1.6; margin-bottom:0;">
                    Verify publication integrity by querying OpenAlex researcher profiles and auditing their papers against RetractionWatch and PubPeer.
                  </p>
                </div>
            </a>
            """,
            unsafe_allow_html=True
        )
                
    st.markdown("<div style='height: 30px;'></div>", unsafe_allow_html=True)
    vis.render_footer()

if __name__ == '__main__':
    main()
