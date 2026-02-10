#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Main entry point for the Conference Organising Committee Identifier (COCI) application.

This script initializes the Streamlit web application, handles the user interface for 
uploading Call for Papers (CfP) files, and orchestrates the processing pipeline 
by invoking functionalities from the `functionalities` module and visualization 
components from `visual_utilities`.

Created on Sun Aug 17 17:55:11 2025

@author: aas358
"""
import streamlit as st
import pandas as pd
from tkinter import filedialog as fd
from io import StringIO



from functionalities import *
from visual_utilities import *




def main():
    """
    The main function of the Streamlit application.

    It performs the following steps:
    1.  Reads the configuration file.
    2.  Sets up the Streamlit page configuration (title, layout, icon).
    3.  Injects custom CSS for styling.
    4.  Renders the sidebar for file uploading and control buttons.
    5.  Handles the 'Process' button click event:
        -   Checks if a file is uploaded.
        -   Determines whether to process the file from scratch or load a cached result.
        -   Calls the processing functions.
        -   Displays the results using visual utility functions.
    6.  Handles the 'Clear' button to reset the application state.
    """
    
    # 1. Load Configuration
    read_config_file()
    
    # 2. Page Setup
    st.set_page_config(
        layout="wide",
        page_title=st.session_state['config']['APP']['app_acronym'],
        page_icon="🌐"
        )
    filename = ""
    call_for_papers = None
    
    ### WEBAPP STYLING
    local('assets/css/bootstrap.min.css')
    local('assets/css/mycss.css')
    
    
    # Main Title
    st.title(st.session_state['config']['APP']['app_name'])  
    
    
    # 3. Sidebar: Input and Controls
    with st.sidebar:
        
        add_logo()
            

        st.title('Load Call for Papers')
        
        
        # File Uploader
        uploaded_file = st.file_uploader("Choose a file")
        if uploaded_file is not None:
            st.write("File loaded")
            filename = uploaded_file.name
            
            # To read file as bytes:
            bytes_data = uploaded_file.getvalue()
        
            # To convert to a string based IO:
            stringio = StringIO(uploaded_file.getvalue().decode("utf-8"))
        
            # To read file as string:
            call_for_papers = stringio.read()
            # print(call_for_papers)
        
        # Force Recompute Option
        to_recompute = st.checkbox("Force", value=False)
        st.write("Selecting **Force** will reprocess the call for papers regardless of whether a cached result exists.")

        
        st.divider()
    
        # Action Buttons
        # Create a container that arranges items horizontally
        with st.container(horizontal=True):
            st.write("") # Placeholder to push button right
            st.write("") 
            submitted = st.button("Process", type="primary")
            
        with st.container(horizontal=True):
            st.write("") # Placeholder to push button right
            st.write("") 
            clear = st.button("Clear", type="secondary")
        
        

    # 4. Event Handling
    if clear:
        st.rerun()
        
        
        
        
    if submitted:
        # Validation
        if call_for_papers is None:
            st.write("Cannot process as no **call for papers** has been provided.")
        
        elif len(call_for_papers) == 0:
            st.write("The **call for papers** file is empty.")
            
        else:
            # Processing Logic
            # Check if we need to run the LLM extraction or if we can use cached JSON
            if not check_if_file_was_previously_processed(filename) or to_recompute:
                # Process from scratch
                conf_data = process_call_for_papers(call_for_papers)
                
                # Save result to cache
                file_path = create_destination_path(filename)
                with open(file_path,'w') as fw:
                    json.dump(conf_data, fw, indent=4)
                    
                display_main(conf_data)
                
            else:
                # Load from cache
                file_path = create_destination_path(filename)
                with open(file_path,'r') as fr:
                    conf_data = json.load(fr)
                    
                    # Refine process (e.g. topic matching) on loaded data
                    conf_data = refine_process(conf_data)
                    
                    display_main(conf_data)
                
                                                
        
    
    
if __name__ == '__main__':
    main()