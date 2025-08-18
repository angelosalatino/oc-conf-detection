#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
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
    
    read_config_file()
    
    st.set_page_config(layout="wide")
    filename = ""
    
    ### WEBAPP
    local('assets/css/bootstrap.min.css')
    local('assets/css/mycss.css')
    
    st.title('Organising Committee Identifier')  
    
    # Sidebar content
    with st.sidebar:
            
        # Using object notation
        st.title('Load Call for Papers')
        
        txt = st.text_area(
            "Either paste the text here",
            "",
        )
        

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
        
        
        to_recompute = st.checkbox("Force", value=False)
        st.write("It will reprocess the call for papers regardless of whether a cached result exists.")

        # if to_recompute:
        #     st.write("Great!")
        
        st.divider()
    
        submitted = st.button("Process", type="primary")
        clear = st.button("Clear", type="secondary")
        
        
        

    if clear:
        st.rerun()
        
        
        
        
    if submitted:
        if not check_if_file_was_previously_processed(filename) or to_recompute:
            conf_data = process_call_for_papers(call_for_papers)
            file_path = create_destination_path(filename)
            with open(file_path,'w') as fw:
                json.dump(conf_data, fw, indent=4)
                
            display_main(conf_data)
            
        else:
            file_path = create_destination_path(filename)
            with open(file_path,'r') as fr:
                conf_data = json.load(fr)
                
                display_main(conf_data)
                
                                                
        
    
    
if __name__ == '__main__':
    main()