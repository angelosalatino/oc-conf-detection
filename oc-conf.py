#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Aug 17 17:55:11 2025

@author: aas358
"""

import streamlit as st
import pandas as pd

from functionalities import *



def remote(url:str)->None:
    st.markdown(f'<link href="{url}" rel="stylesheet">', unsafe_allow_html=True)
    
def local(file_name:str)->None:
    with open(file_name) as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

def main():
    ### WEBAPP
    local('assets/css/bootstrap.min.css')
    
    
if __name__ == '__main__':
    main()