#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Aug 18 09:29:17 2025

@author: aas358
"""
import streamlit as st
from streamlit_extras.stylable_container import stylable_container
# import tkinter as tk
# from tkinter import filedialog
import pandas as pd
import base64
from io import BytesIO
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
    
    image_url = ""
    if title == "DBLP": image_url = "assets/images/dblp_total.png"
    elif title == "AIDA Dashboard": image_url = "assets/images/AIDA-dashboard.png"
    elif title == "ConfIDent": image_url = "assets/images/ConfIDent_TIB_Logo.png"        
    else: print(f"Error. Card creation requested with title {title}")
    
    html_bit = f"""<div class="card text-center mb-3" style="background-color: {color};">
             <div class="card-header">
               <img class="logo" src={render_image(image_url)}/>
             </div>
          <div class="card-body">
              <h4 class="card-title" style="padding: 0;">{title}</h4> 
              <p class="card-text">{value}</p>
              """
    if len(link) > 0:
        html_bit += f"""<a href="{link}" class="btn oc-btn" target="_blank">{link_text}</a>"""
        
        
    html_bit += "</div></div>"
              
    
    
    st.write(html_bit, unsafe_allow_html=True)
        

        
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
        
        


def render_image(filepath: str):
   """
   filepath: path to the image. Must have a valid file extension.
   """
   mime_type = filepath.split('.')[-1:][0].lower()
   with open(filepath, "rb") as f:
       content_b64encoded = base64.b64encode(f.read())
       image_string = "data:image/png;base64," + content_b64encoded.decode("utf-8")
   return image_string[:-2]
        
        
def display_main(conf_data:dict)->None:
    
    ##### PROCESS DATA
    
    organisers = pd.DataFrame.from_dict(conf_data["organisers"])
    organisers = organisers[["organiser_name",
                             "openalex_name",
                             "openalex_page",
                             "orcid",
                             "organiser_affiliation",
                             "affiliation_ror",
                             "organiser_country",
                             "track_name"]]
    organisers = organisers.rename(columns={"organiser_name": "Name",
                                        "organiser_affiliation": "Affiliation",
                                        "organiser_country": "Country",
                                        "track_name": "Track",
                                        "affiliation_ror": "ROR",
                                        "openalex_page": "OpenAlex Profile",
                                        "orcid": "ORCID",
                                        "openalex_name": "OpenAlex Name"
                                        })
    
    
    conf_info = dict()
    conf_info["Event"] = conf_data["event_name"]
    conf_info["Acronym"] = conf_data["event_acronym"]
    conf_info["Conference Series"] = conf_data["conference_series"]
    if len(conf_data["colocated_with"]) > 0: conf_info["Co-located with"] = conf_data["colocated_with"]
    conf_info["Location"] = conf_data["location"]
    if len(conf_data["DBLP"]) > 0: conf_info["DBLP url"] = conf_data['DBLP']['url']
    if len(conf_data["AIDA"]) > 0: conf_info["AIDA url"] = conf_data['AIDA']['url']
    if len(conf_data["ConfIDent"]) > 0: conf_info["ConfIDent url"] = conf_data['ConfIDent']['url']

    conf_info_df = pd.DataFrame(conf_info.items(), columns=['Info', 'Value'])
    
    
    
    
    ##### DISPLAY
    
    
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
    

    

    
    
    
    st.dataframe(organisers,
        column_config={
            "ROR": st.column_config.LinkColumn("ROR",display_text=r"https://ror\.org/(.*)"),
            "OpenAlex Profile": st.column_config.LinkColumn("OpenAlex Profile",display_text=r"https://openalex\.org/(.*)"),
            "ORCID": st.column_config.LinkColumn("ORCID",display_text=r"https://orcid\.org/(.*)"),
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
            card_w_l("DBLP","No information found on DBLP about this conference.")
    with dfColumns[1]:
        if len(conf_data["AIDA"]) > 0:
            card_w_l("AIDA Dashboard",
                     f"Matched this conference with the {conf_data['AIDA']['name']} (id: <b>{conf_data['AIDA']['id']}</b>) instance on the AIDA Dashboard.", 
                     conf_data['AIDA']['url'],
                     "Conference on the AIDA Dashboard")
        else:
            card_w_l("AIDA Dashboard","No information found on the AIDA Dashboard about this conference.")
    with dfColumns[2]:
        if len(conf_data["ConfIDent"]) > 0:
            card_w_l("ConfIDent",
                     f"Matched this conference with the {conf_data['ConfIDent']['name']} (id: <b>{conf_data['ConfIDent']['id']}</b>) instance on the Conference ConfIDent.", 
                     conf_data['ConfIDent']['url'],
                     "Conference on ConfIDent")
        else:
            card_w_l("ConfIDent","No information found on ConfIDent database about this conference.")

    st.divider()
            
    ######### EXPORT DATA   
    # buffer to use for excel writer
    buffer = BytesIO()
    
    export_file = conf_data["event_name"]
    
    
    
    # download button to download dataframe as xlsx
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        # Write each dataframe to a different worksheet.
        organisers.to_excel(writer, sheet_name='Organisers', index=True)
        conf_info_df.to_excel(writer, sheet_name='Conference Info', index=True)
        writer._save()
        with stylable_container(
            key="download_data",
            css_styles="""
            button{
                float: right;
            }
            """
        ):
            download2 = st.download_button(
                label="Download data as Excel",
                data=buffer,
                file_name=f"{export_file}.xlsx",
                mime='application/vnd.ms-excel',
            )
       
            

