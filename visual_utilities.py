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





def card(title:str, value:str="", color:str="#f0f2f6")->None:
    """
    Generates the HTML of a simple card. No link, no image.

    Parameters
    ----------
    title : str
        Title of the card.
    value : str, optional
        Content of the card. The default is "".
    color : str, optional
        Background color of the card. The default is "#f0f2f6".

    Returns
    -------
    None
        The card will be diplayed. Nothing is returned.

    """
    st.html(f"""<div class="card text-center mb-3" style="background-color: {color};">
          <div class="card-body">
              <h4 class="card-title" style="padding: 0;">{title}</h4> 
              <p class="card-text">{value}</p>
          </div>
        </div>
        """)
        
def card_w_l(title:str, value:str="", link:str="", link_text:str="Visit", color:str="#f0f2f6")->None:
    """
    Generates the HTML of a card

    Parameters
    ----------
    title : str
        Title of the card.
    value : str, optional
        Content of the card. The default is "".
    link : str, optional
        The URL for the button link. If there is no need for a link, leave empty. The default is "".
    link_text : str, optional
        The surface form of the link: eg. Visit Conference on DBLP. The default is "Visit".
    color : str, optional
        Background color of the card. The default is "#f0f2f6".

    Returns
    -------
    None
        The card will be diplayed. Nothing is returned.

    """
    
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
        
        
        
def remote(url:str)->None:
    st.markdown(f'<link href="{url}" rel="stylesheet">', unsafe_allow_html=True)
    
def local(file_name:str)->None:
    with open(file_name) as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
        

def add_logo():
    image_string = render_image('assets/images/coci_logo.png')
    st.markdown(
        """
        <style>
            [data-testid="stSidebarNav"] {
                background-image: url(%s);
                height: 200px;
                background-repeat: no-repeat;
                padding-top: 150px;
                background-position: 20px 0px;
                background-size: 240px 120px;
            }
        </style>
        """ % image_string,
        unsafe_allow_html=True,
    )
    

def render_image(filepath: str)->str:
    """
    

    Parameters
    ----------
    filepath : str
        path to the image. Must have a valid file extension..

    Returns
    -------
    str
        the base64 string of the image.

    """
    mime_type = filepath.split('.')[-1:][0].lower()
    with open(filepath, "rb") as f:
        content_b64encoded = base64.b64encode(f.read())
        image_string = "data:image/png;base64," + content_b64encoded.decode("utf-8")
    return image_string[:-2]
        
        
def display_main(conf_data:dict)->None:
    """
    

    Parameters
    ----------
    conf_data : dict
        Dictionary containing the conference information.

    Returns
    -------
    None
        Nothng is returned as this function displays the content.

    """
    
    ##### PROCESS DATA
    
    # # clean the track name, as it is harder to do this via LLM
    # tracks = set()
    # for organiser in conf_data["organisers"]:
    #     tracks.add(organiser["track_name"])
        
    # print(tracks)
    # print(len(tracks))
    
    # multi_track = True if len(tracks) > 1 else False
    # if multi_track:
    #     for organiser in conf_data["organisers"]:
    #         if organiser["track_name"].lower() == "main":
    #             print("Changed")
    #             organiser["track_name"] = "Other"
    
    ## Preparing the table for the organisers
    
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
    
    # removes empty columns (as not all the info is avaible, such as affiliation)   
    def check_series(x):
        for i in x:
            if len(i) > 0:
                return True
        return False

    final_list_columns = organisers.apply(lambda x: check_series(x), axis=0)
    organisers = organisers[final_list_columns[final_list_columns==True].index]
    
    
    # this is mostly useful for the export in excel
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
    
    ## First part: conference information 
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
    
    
    ## Second part: organisers, table
    
    st.dataframe(organisers,
        column_config={
            "ROR": st.column_config.LinkColumn("ROR",display_text=r"https://ror\.org/(.*)"),
            "OpenAlex Profile": st.column_config.LinkColumn("OpenAlex Profile",display_text=r"https://openalex\.org/(.*)"),
            "ORCID": st.column_config.LinkColumn("ORCID",display_text=r"https://orcid\.org/(.*)"),
        },
        # hide_index=True,
        width=1920
    )
    
        
    ## Third part: showing mapping of conference toward other datasets.
    
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
            download = st.download_button(
                label="Download data as Excel",
                data=buffer,
                file_name=f"{export_file}.xlsx",
                mime='application/vnd.ms-excel',
            )
            
            
    ## END of main display

            

