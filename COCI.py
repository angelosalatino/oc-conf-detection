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
from classes.storage import ConferenceStorage

def read_config_file():
    if 'config' not in st.session_state:
        st.session_state['config'] = configparser.ConfigParser()
        st.session_state['config'].read('config.ini')

def main():
    read_config_file()
    
    dest_folder = st.session_state['config']['FOLDERS']['destination_folder']
    storage = ConferenceStorage(dest_folder)
    
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
    welcome_placeholder.markdown(f"<h4 style='text-align: left; color: gray;'>Welcome to the Conference Organisers and Content Identifier (COCI), an AI-powered tool for extracting and structuring metadata from <i><u>calls for papers</u></i>. To begin, please upload your CfP as a .txt file using the sidebar on the left to automatically identify conference details, organizers, and research topics.</h4>", unsafe_allow_html=True)
    
    with st.sidebar:
        vis.add_logo()
        st.title('Load Call for Papers')
        
        uploaded_file = st.file_uploader("Choose a file")
        if uploaded_file is not None:
            st.write("File loaded")
            filename = uploaded_file.name
            cfp = CallForPaper(uploaded_file)
            call_for_papers = cfp.text
        
        processing_mode = st.radio(
            "Processing Mode",
            options=["Cached", "Mild Force", "Force"],
            index=0
        )
        st.caption("**Cached**: Uses cache if available.  \n**Mild Force**: Reuses LLM extractions but reruns matching.  \n**Force**: Reprocesses everything from scratch.")
        to_recompute = (processing_mode == "Force")
        mild_force = (processing_mode == "Mild Force")
        
        st.divider()
        with st.container(horizontal=True):
            st.write("") 
            st.write("") 
            submitted = st.button("Process", type="primary")
            
        with st.container(horizontal=True):
            st.write("") 
            st.write("") 
            clear = st.button("Clear", type="secondary")
            
        st.html("<div style='height: 120px;'></div>")

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
            cached_llm_result = None
            if mild_force and not to_recompute and storage.is_processed(filename):
                loaded_data = storage.load(filename)
                cached_llm_result = loaded_data.get("llm-output")

            if not storage.is_processed(filename) or to_recompute or mild_force:
                api_url = st.session_state['config']['DEFAULT']['api_url']
                api_key = st.session_state['config']['DEFAULT']['api_key']
                referer = st.session_state['config']['TEAM']['website']
                title = st.session_state['config']['TEAM']['description']
                
                progress_placeholder = st.empty()
                logs = []
                
                def update_progress(message: str):
                    logs.append(message)
                    logs_html = "<br>".join([f"&gt; {msg}" for msg in logs])
                    spinner_html = f'''
                    <div style="display: flex; align-items: flex-start; margin-bottom: 20px; background-color: #f4f6f9; padding: 15px; border-radius: 5px; border: 1px solid #ddd;">
                        <img src="{vis.render_image('assets/gifs/cooking.gif')}" width="60" height="60" style="margin-right: 15px; margin-top: 5px;" />
                        <div style="font-size: 14px; font-family: monospace; color: #333;">
                            {logs_html}
                        </div>
                    </div>
                    '''
                    progress_placeholder.markdown(spinner_html, unsafe_allow_html=True)
                
                orchestrator = Orchestrator(api_url, api_key, referer, title)
                conf, llm_result = orchestrator.process(call_for_papers, progress_callback=update_progress, cached_llm_result=cached_llm_result)
                
                progress_placeholder.empty()
                
                storage.save(filename, conf.to_dict(), llm_result)
            else:
                loaded_data = storage.load(filename)
                conf = Conference.from_dict(loaded_data.get("processed"))
            
            tab1, tab2 = st.tabs(["**Results**", "**Read Call for Papers**"])
            
            with tab1:
                vis.display_main(conf)
                
            with tab2:
                cfp_obj = CallForPaper(call_for_papers)
                st.html(cfp_obj.get_rendered_html())

if __name__ == '__main__':
    main()
