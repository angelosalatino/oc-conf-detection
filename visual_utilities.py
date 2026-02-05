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
    Generates and displays the HTML of a simple card component. No link, no image.

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
        The card will be displayed in the Streamlit app. Nothing is returned.

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
    Generates and displays the HTML of a card component with an image and an optional link.

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
        The card will be displayed in the Streamlit app. Nothing is returned.

    """
    
    # Determine the image URL based on the card title
    image_url = ""
    if title == "DBLP": image_url = "assets/images/dblp_total.png"
    elif title == "AIDA Dashboard": image_url = "assets/images/AIDA-dashboard.png"
    elif title == "ConfIDent": image_url = "assets/images/ConfIDent_TIB_Logo.png"        
    else: print(f"Error. Card creation requested with title {title}")
    
    # Construct the HTML structure for the card
    html_bit = f"""<div class="card text-center mb-3" style="background-color: {color};">
             <div class="card-header">
               <img class="logo" src={render_image(image_url)}/>
             </div>
          <div class="card-body">
              <h4 class="card-title" style="padding: 0;">{title}</h4> 
              <p class="card-text">{value}</p>
              """
    # Add the link button if a URL is provided
    if len(link) > 0:
        html_bit += f"""<a href="{link}" class="btn oc-btn" target="_blank">{link_text}</a>"""
        
        
    html_bit += "</div></div>"
              
    
    st.write(html_bit, unsafe_allow_html=True)
        
        
        
def remote(url:str)->None:
    """
    Injects a remote CSS stylesheet into the Streamlit app.

    Parameters
    ----------
    url : str
        The URL of the CSS file.
    """
    st.markdown(f'<link href="{url}" rel="stylesheet">', unsafe_allow_html=True)
    
def local(file_name:str)->None:
    """
    Injects a local CSS file into the Streamlit app.

    Parameters
    ----------
    file_name : str
        Path to the local CSS file.
    """
    with open(file_name) as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
        

def add_logo():
    """
    Adds a custom logo to the Streamlit sidebar navigation using CSS injection.
    """
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
    Converts an image file to a base64 encoded string for embedding in HTML.

    Parameters
    ----------
    filepath : str
        Path to the image file. Must have a valid file extension.

    Returns
    -------
    str
        The base64 encoded string of the image, prefixed with the data URI scheme.

    """
    mime_type = filepath.split('.')[-1:][0].lower()
    with open(filepath, "rb") as f:
        content_b64encoded = base64.b64encode(f.read())
        image_string = "data:image/png;base64," + content_b64encoded.decode("utf-8")
    return image_string[:-2]
        
        
def display_main(conf_data:dict)->None:
    """
    Displays the main content of the application, including conference details,
    organisers table, and links to external datasets.

    Parameters
    ----------
    conf_data : dict
        Dictionary containing the structured conference information.

    Returns
    -------
    None
        Nothing is returned as this function renders content directly to Streamlit.

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
    
    # Create a DataFrame from the organisers list
    organisers = pd.DataFrame.from_dict(conf_data["organisers"])
    organisers = organisers[["organiser_name",
                             "openalex_name",
                             "openalex_page",
                             "orcid",
                             "organiser_affiliation",
                             "affiliation_ror",
                             "organiser_country",
                             "track_name",
                             "verified"]]
    
    # Rename columns for better display in the UI
    organisers = organisers.rename(columns={"organiser_name": "Name",
                                        "organiser_affiliation": "Affiliation",
                                        "organiser_country": "Country",
                                        "track_name": "Track",
                                        "affiliation_ror": "ROR",
                                        "openalex_page": "OpenAlex Profile",
                                        "orcid": "ORCID",
                                        "openalex_name": "OpenAlex Name"
                                        })
    
    # Helper function to check if a column has any valid data (non-empty strings or True booleans)
    def check_series(x):
        for i in x:
            if type(i) == bool and i == True:
                return True
            elif type(i) != bool and len(i) > 0:
                return True
        return False

    # Filter out columns that are completely empty
    final_list_columns = organisers.apply(lambda x: check_series(x), axis=0)
    organisers = organisers[final_list_columns[final_list_columns==True].index]
    
    
    # Prepare conference info dictionary for Excel export
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
    if len(conf_data["year"]) > 0:
        description += f"<br>({conf_data['year']} edition)"
    
    card(conf_data["event_name"],description)
    
    
    ## Second part: organisers, table
    
    # Create a copy for display modification
    organisers_mod = organisers.copy(deep=True)
    
    # Mark verified affiliations with a star symbol
    if 'verified' in organisers_mod: # just because it could have gotten cleaned
        organisers_mod.loc[organisers_mod['verified'] == True, 'Affiliation'] = organisers_mod['Affiliation'] + ' ✪'
        organisers_mod = organisers_mod.drop(columns=['verified'])
    
    # Display the dataframe with configured link columns
    st.dataframe(organisers_mod,
        column_config={
            "ROR": st.column_config.LinkColumn("ROR",display_text=r"https://ror\.org/(.*)"),
            "OpenAlex Profile": st.column_config.LinkColumn("OpenAlex Profile",display_text=r"https://openalex\.org/(.*)"),
            "ORCID": st.column_config.LinkColumn("ORCID",display_text=r"https://orcid\.org/(.*)"),
        },
        # hide_index=True,
        width=1920
    )
    
        
    ## Third part: showing mapping of conference toward other datasets.
    
    # Create three columns for DBLP, AIDA, and ConfIDent cards
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
    # Buffer to use for excel writer
    buffer = BytesIO()
    
    export_file = conf_data["event_name"]
    
    
    
    # Create Excel file in memory and provide download button
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

            
