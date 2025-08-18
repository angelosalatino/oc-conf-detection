#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Aug 18 09:29:17 2025

@author: aas358
"""
import streamlit as st
import tkinter as tk
from tkinter import filedialog
import pandas as pd
import os



def card(title, value="", color="#f0f2f6"):
    st.html(f"""<div class="card text-center mb-3" style="background-color: {color};">
          <div class="card-body">
              <h4 class="card-title" style="padding: 0;">{title}</h4> 
              <p class="card-text">{value}</p>
          </div>
        </div>
        """)
        
def card_w_l(title, value="", link="", link_text="Visit", color="#f0f2f6"):
    st.write(f"""<div class="card text-center mb-3" style="background-color: {color};">
          <div class="card-body">
              <h4 class="card-title" style="padding: 0;">{title}</h4> 
              <p class="card-text">{value}</p>
              <a href="{link}" class="btn oc-btn" target="_blank">{link_text}</a>
        </div>
        </div>
        """, unsafe_allow_html=True)
        

        
def cardb(description, color="#f0f2f6"):
    st.html(f"""<div class="card text-center mb-3" style="background-color: {color};">
          <div class="card-body">
              <p class="card-text" style="padding: 0;">{description}</p>
          </div>
        </div>
        """)
        
        
def remote(url:str)->None:
    st.markdown(f'<link href="{url}" rel="stylesheet">', unsafe_allow_html=True)
    
def local(file_name:str)->None:
    with open(file_name) as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
        
        
def display_main(conf_data:dict)->None:
    description = ""
    if len(conf_data["conference_series"]) >0:
        description += conf_data["conference_series"]
    if len(conf_data["event_acronym"]) >0:
        description += f" ({conf_data['event_acronym']})"
    if len(conf_data["colocated_with"]) > 0:
        description += f"<br> co-located with {conf_data['colocated_with']}"
    if len(conf_data["location"]) > 0:
        description += f"<br> held in {conf_data['location']}"
    
    card(conf_data["event_name"],description)
    
    organisers = pd.DataFrame.from_dict(conf_data["organisers"])
    organisers = organisers[["organiser_name",
                             "openalex_name",
                             "openalex_page",
                             "orcid",
                             "organiser_affiliation",
                             "affiliation_ror",
                             "organiser_country",
                             "track_name"]]
    
    st.dataframe(organisers,
        column_config={
            "organiser_name": "Name",
            "organiser_affiliation": "Affiliation",
            "organiser_country": "Country",
            "track_name": "Track",
            "affiliation_ror": st.column_config.LinkColumn("ROR",display_text=r"https://ror\.org/(.*)"),
            "openalex_page": st.column_config.LinkColumn("OpenAlex Profile",display_text=r"https://openalex\.org/(.*)"),
            "orcid": st.column_config.LinkColumn("ORCID",display_text=r"https://orcid\.org/(.*)"),
            "openalex_name": "OpenAlex Name"
        },
        # hide_index=True,
        width=1920
    )
        
    
    dfColumns = st.columns(3)
    with dfColumns[0]:
        if len(conf_data["DBLP"]) > 0:
            card_w_l("DBLP",
                     f"Matched this conference with the {conf_data['DBLP']['name']} (id: <b>{conf_data['DBLP']['id']}</b>) instance on DBLP.", 
                     conf_data['DBLP']['url'],
                     "Conference on DBLP")
        else:
            card("DBLP","No information found on DBLP about this conference.")
    with dfColumns[1]:
        if len(conf_data["AIDA"]) > 0:
            card_w_l("AIDA Dashboard",
                     f"Matched this conference with the {conf_data['AIDA']['name']} (id: <b>{conf_data['AIDA']['id']}</b>) instance on the AIDA Dashboard.", 
                     conf_data['AIDA']['url'],
                     "Conference on the AIDA Dashboard")
        else:
            card("AIDA Dashboard","No information found on the AIDA Dashboard about this conference.")
    with dfColumns[2]:
        if len(conf_data["ConfIDent"]) > 0:
            card_w_l("ConfIDent",
                     f"Matched this conference with the {conf_data['ConfIDent']['name']} (id: <b>{conf_data['ConfIDent']['id']}</b>) instance on the Conference ConfIDent.", 
                     conf_data['ConfIDent']['url'],
                     "Conference on ConfIDent")
        else:
            card("ConfIDent","No information found on ConfIDent database about this conference.")