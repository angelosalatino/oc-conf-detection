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

def main():
    read_config_file()
    check_page_change("process_events")
    
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

    with st.sidebar:
        vis.add_logo()
    
    # Manage processing states
    if 'processed_conf' not in st.session_state:
        st.session_state['processed_conf'] = None
    if 'processed_filename' not in st.session_state:
        st.session_state['processed_filename'] = ""
    if 'processed_cfp_text' not in st.session_state:
        st.session_state['processed_cfp_text'] = ""
        
    # BACK BUTTON VIEW (if processed)
    if st.session_state['processed_conf'] is not None:
        if st.button("← Back to upload form", type="secondary"):
            st.session_state['processed_conf'] = None
            st.session_state['processed_filename'] = ""
            st.session_state['processed_cfp_text'] = ""
            st.rerun()
            
        st.divider()
        conf = st.session_state['processed_conf']
        filename = st.session_state['processed_filename']
        call_for_papers = st.session_state['processed_cfp_text']
        
        tab1, tab2 = st.tabs(["**Results**", "**Read Call for Papers**"])
        with tab1:
            vis.display_main(conf, filename, storage)
        with tab2:
            cfp_obj = CallForPaper(call_for_papers)
            st.html(cfp_obj.get_rendered_html())
            
    # UPLOAD FORM VIEW
    else:
        # st.markdown(f"<h4 style='text-align: left; color: gray; margin-bottom: 30px;'>Welcome to the Conference Organisers and Content Identifier (COCI), an AI-powered tool for extracting and structuring metadata from <i><u>calls for papers</u></i>. Please upload your CfP as a .txt file using the form below to automatically identify conference details, organizers, and research topics.</h4>", unsafe_allow_html=True)
        st.markdown("Please upload your CfP as a .txt file using the form below to automatically identify conference details, organizers, and research topics.")
        margin_left_col, main_col, margin_right_col = st.columns([1, 2, 1])
        with main_col:
            # st.markdown("### Upload Call for Papers")
            uploaded_file = st.file_uploader("Choose a file", type=["txt"])
            
            filename = ""
            call_for_papers = None
            if uploaded_file is not None:
                filename = uploaded_file.name
                cfp = CallForPaper(uploaded_file)
                call_for_papers = cfp.text

            # st.markdown("### Processing Mode")
            st.caption("**Cached**: Uses cache if available. **Mild Force**: Reuses LLM extractions but reruns matching. **Force**: Reprocesses everything from scratch.")
            processing_mode = st.radio(
                "Select Mode",
                options=["Cached", "Mild Force", "Force"],
                index=0,
                label_visibility="collapsed",
                horizontal=True
            )

            to_recompute = (processing_mode == "Force")
            mild_force = (processing_mode == "Mild Force")
            
            # st.divider()
            btn_col1, btn_col2 = st.columns(2)
            with btn_col1:
                submitted = st.button("Process", type="primary", use_container_width=True)
            with btn_col2:
                clear = st.button("Clear", type="secondary", use_container_width=True)
                
        if clear:
            st.rerun()
            
        if submitted:
            if call_for_papers is None:
                st.error("Cannot process as no **call for papers** has been provided.")
            elif len(call_for_papers) == 0:
                st.error("The **call for papers** file is empty.")
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
                    openalex_api = st.session_state['config']['OPENALEX']['openalex_api']
                    
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
                    
                    orchestrator = Orchestrator(api_url, api_key, referer, title, openalex_api)
                    conf, llm_result = orchestrator.process(call_for_papers, progress_callback=update_progress, cached_llm_result=cached_llm_result)
                    
                    progress_placeholder.empty()
                    
                    storage.save(filename, conf.to_dict(), llm_result, call_for_papers)
                else:
                    loaded_data = storage.load(filename)
                    conf = Conference.from_dict(loaded_data.get("processed"))
                    if not call_for_papers and loaded_data.get("cfp_text"):
                        call_for_papers = loaded_data["cfp_text"]
                
                st.session_state['processed_conf'] = conf
                st.session_state['processed_filename'] = filename
                st.session_state['processed_cfp_text'] = call_for_papers
                st.rerun()
    vis.render_footer()

if __name__ == '__main__':
    main()
