import streamlit as st
import json
import os
import configparser
from io import StringIO
import html
from pathlib import Path

from classes.orchestrator import Orchestrator
from classes.visualiser import ConferenceVisualiser
from classes.conference import Conference
from classes.call_for_paper import CallForPaper

def read_config_file():
    if 'config' not in st.session_state:
        st.session_state['config'] = configparser.ConfigParser()
        st.session_state['config'].read('config.ini')

def create_destination_path(filename: str) -> str:
    cut_filename = Path(filename).stem
    return f"{st.session_state['config']['FOLDERS']['destination_folder']}/{cut_filename}.json"

def check_if_file_was_previously_processed(filename: str) -> bool:
    my_file = Path(create_destination_path(filename))
    return my_file.is_file()

def main():
    read_config_file()
    
    st.set_page_config(
        layout="wide",
        page_title=st.session_state['config']['APP']['app_acronym'],
        page_icon="🌐"
    )
    
    filename = ""
    call_for_papers = None
    
    vis = ConferenceVisualiser()
    
    vis.local('assets/css/bootstrap.min.css')
    vis.local('assets/css/mycss.css')
    
    st.title(st.session_state['config']['APP']['app_name'])
    welcome_placeholder = st.empty()
    welcome_placeholder.markdown(f"<h4 style='text-align: left; color: gray;'>Welcome to the Conference Organisers and Content Identifier (COCI), an AI-powered tool for extracting and structuring metadata from calls for papers. To begin, please upload your CfP as a .txt file using the sidebar on the left to automatically identify conference details, organizers, and research topics.</h4>", unsafe_allow_html=True)
    
    with st.sidebar:
        vis.add_logo()
        st.title('Load Call for Papers')
        
        uploaded_file = st.file_uploader("Choose a file")
        if uploaded_file is not None:
            st.write("File loaded")
            filename = uploaded_file.name
            cfp = CallForPaper(uploaded_file)
            call_for_papers = cfp.text
        
        to_recompute = st.checkbox("Force", value=False)
        st.write("Selecting **Force** will reprocess the call for papers regardless of whether a cached result exists.")
        
        st.divider()
        with st.container(horizontal=True):
            st.write("") 
            st.write("") 
            submitted = st.button("Process", type="primary")
            
        with st.container(horizontal=True):
            st.write("") 
            st.write("") 
            clear = st.button("Clear", type="secondary")

    if clear:
        st.rerun()
        
    vis.render_footer()
        
    if submitted:
        welcome_placeholder.empty()
        if call_for_papers is None:
            st.write("Cannot process as no **call for papers** has been provided.")
        elif len(call_for_papers) == 0:
            st.write("The **call for papers** file is empty.")
        else:
            if not check_if_file_was_previously_processed(filename) or to_recompute:
                api_url = st.session_state['config']['DEFAULT']['api_url']
                api_key = st.session_state['config']['DEFAULT']['api_key']
                referer = st.session_state['config']['TEAM']['website']
                title = st.session_state['config']['TEAM']['description']
                
                orchestrator = Orchestrator(api_url, api_key, referer, title)
                conf = orchestrator.process(call_for_papers)
                
                file_path = create_destination_path(filename)
                with open(file_path, 'w') as fw:
                    json.dump(conf.to_dict(), fw, indent=4)
            else:
                file_path = create_destination_path(filename)
                with open(file_path, 'r') as fr:
                    conf_data = json.load(fr)
                
                conf = Conference.from_dict(conf_data)
            
            tab1, tab2 = st.tabs(["**Results**", "**Read Call for Papers**"])
            
            with tab1:
                vis.display_main(conf)
                
            with tab2:
                safe_text = html.escape(call_for_papers)
                st.markdown(f"<div style='white-space: pre-wrap; font-family: monospace; background-color: #f4f6f9; padding: 15px; border-radius: 5px; border: 1px solid #ddd;'>{safe_text}</div>", unsafe_allow_html=True)

if __name__ == '__main__':
    main()
