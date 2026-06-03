import streamlit as st
import pandas as pd
from io import BytesIO
import base64
import os
import html
from .conference import Conference

class CoreVisualiser:
    def __init__(self):
        pass

    def card(self, title: str, value: str = "", color: str = "#f0f2f6") -> None:
        st.html(f"""<div class="card text-center mb-3" style="background-color: {color};">
              <div class="card-body">
                  <h4 class="card-title" style="padding: 0;">{title}</h4> 
                  <p class="card-text">{value}</p>
              </div>
            </div>
            """)
            
    def card_w_l(self, title: str, value: str = "", link: str = "", link_text: str = "Visit", color: str = "#f0f2f6") -> None:
        image_url = ""
        if title == "DBLP": image_url = "assets/images/dblp_total.png"
        elif title == "AIDA Dashboard": image_url = "assets/images/AIDA-dashboard.png"
        elif title == "ConfIDent": image_url = "assets/images/ConfIDent_TIB_Logo.png"        
        else: print(f"Error. Card creation requested with title {title}")
        
        html_bit = f"""<div class="card text-center mb-3" style="background-color: {color};">
                 <div class="card-header">
                   <img class="logo" src={self.render_image(image_url)}/>
                 </div>
              <div class="card-body">
                  <h4 class="card-title" style="padding: 0;">{title}</h4> 
                  <p class="card-text">{value}</p>
                  """
        if len(link) > 0:
            html_bit += f"""<a href="{link}" class="btn oc-btn" target="_blank">{link_text}</a>"""
            
        html_bit += "</div></div>"
        st.write(html_bit, unsafe_allow_html=True)

    def remote(self, url: str) -> None:
        st.markdown(f'<link href="{url}" rel="stylesheet">', unsafe_allow_html=True)
        
    def local(self, file_name: str) -> None:
        with open(file_name) as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

    def add_logo(self):
        image_string = self.render_image('assets/images/coci_logo.png')
        st.markdown(
            """
            <style>
                [data-testid="stSidebarNav"] {
                    background-image: url(%s);
                    background-repeat: no-repeat;
                    padding-top: 150px;
                    background-position: 20px 0px;
                    background-size: 240px 120px;
                }
            </style>
            """ % image_string,
            unsafe_allow_html=True,
        )
        
    def add_header(self, text: str, level: int = 2):
        st.markdown(f"<h{level}>{text}</h{level}>", unsafe_allow_html=True)
        
    def render_image(self, filepath: str) -> str:
        mime_type = filepath.split('.')[-1:][0].lower()
        with open(filepath, "rb") as f:
            content_b64encoded = base64.b64encode(f.read())
            image_string = "data:image/png;base64," + content_b64encoded.decode("utf-8")
        return image_string[:-2]

    def get_image_as_base64(self, path):
        try:
            with open(path, "rb") as image_file:
                encoded = base64.b64encode(image_file.read()).decode()
                ext = os.path.splitext(path)[1].lower()
                mime = "image/jpeg" if ext in [".jpg", ".jpeg"] else "image/png"
                return f"data:{mime};base64,{encoded}"
        except Exception:
            return "https://via.placeholder.com/120x40?text=Image+Not+Found"

    def render_footer(self):
        footer = f"""
        <style>
        .custom-footer {{
            position: fixed;
            left: 0;
            bottom: 0;
            width: 100%;
            background-color: #183642;
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 20px 150px;
            border-top: 1px solid #eaeaea;
            z-index: 999999;
        }}
        .custom-footer img {{
            height: 50px;       
            object-fit: contain;
        }}
        /* Hide Streamlit default footer so it doesn't overlap */
        footer {{visibility: hidden;}}
        </style>
        <div class="custom-footer">
            <div>
                <img src="{self.get_image_as_base64('assets/logos/KMi-logo-white.png')}" alt="KMi Logo">
            </div>
            <div>
                <img src="{self.get_image_as_base64('assets/logos/ou-logo-white.png')}" alt="Open University Logo">
            </div>
            <div>
                <img src="{self.get_image_as_base64('assets/logos/sn-logo-white.png')}" alt="Springer Nature Logo">
            </div>
        </div>
        """
        st.markdown(footer, unsafe_allow_html=True)


class ConferenceVisualiser(CoreVisualiser):
    def display_main(self, conf: Conference, filename: str = None, storage = None) -> None:
        organisers_data = conf.organisers.to_dict() if conf.organisers else []
        organisers_df = pd.DataFrame.from_dict(organisers_data)
        
        expected_columns = [
            "organiser_name", "openalex_name", "openalex_page", "orcid",
            "organiser_affiliation", "affiliation_ror", "organiser_country",
            "track_name", "verified"
        ]
        organisers_df = organisers_df.reindex(columns=expected_columns)
        
        organisers_df = organisers_df.rename(columns={"organiser_name": "Name",
                                            "organiser_affiliation": "Affiliation",
                                            "organiser_country": "Country",
                                            "track_name": "Track",
                                            "affiliation_ror": "ROR",
                                            "openalex_page": "OpenAlex Profile",
                                            "orcid": "ORCID",
                                            "openalex_name": "OpenAlex Name"
                                            })
        
        def check_series(x):
            for i in x:
                if isinstance(i, bool) and i is True:
                    return True
                elif not isinstance(i, bool) and pd.notnull(i) and len(str(i)) > 0:
                    return True
            return False

        final_list_columns = organisers_df.apply(lambda x: check_series(x), axis=0)
        organisers_df = organisers_df[final_list_columns[final_list_columns==True].index]
        
        conf_info = dict()
        conf_info["Event"] = conf.name
        conf_info["Acronym"] = conf.acronym
        conf_info["Conference Series"] = conf.series
        if len(conf.colocated) > 0: conf_info["Co-located with"] = conf.colocated
        conf_info["Location"] = conf.location
        if conf.dblp: conf_info["DBLP url"] = conf.dblp.get('url', '')
        if conf.aida: conf_info["AIDA url"] = conf.aida.get('url', '')
        if conf.confident: conf_info["ConfIDent url"] = conf.confident.get('url', '')

        conf_info_df = pd.DataFrame(conf_info.items(), columns=['Info', 'Value'])
        
        description = ""
        if len(conf.series) > 0:
            description += conf.series
        if len(conf.acronym) > 0:
            description += f" ({conf.acronym})"
        if len(conf.colocated) > 0:
            description += f"<br> co-located with {conf.colocated}"
        if len(conf.location) > 0:
            description += f"<br> held in {conf.location}"
        if len(conf.year) > 0:
            description += f" ({conf.year} edition)"
        
        self.card(conf.name, description)
        
        organisers_mod = organisers_df.copy(deep=True)
        if 'verified' in organisers_mod:
            organisers_mod.loc[organisers_mod['verified'] == True, 'Affiliation'] = organisers_mod['Affiliation'] + ' ✪'
            organisers_mod = organisers_mod.drop(columns=['verified'])
        
        self.add_header("Organisers")
        if organisers_mod.empty:
            st.write("No organisers found.")
        else:
            st.dataframe(organisers_mod,
                column_config={
                    "ROR": st.column_config.LinkColumn("ROR", display_text=r"https://ror\.org/(.*)"),
                    "OpenAlex Profile": st.column_config.LinkColumn("OpenAlex Profile", display_text=r"https://openalex\.org/(.*)"),
                    "ORCID": st.column_config.LinkColumn("ORCID", display_text=r"https://orcid\.org/(.*)"),
                },
                width=1920
            )
        
        self.add_header("Conference on External Indexes")
        dfColumns = st.columns(3)
        with dfColumns[0]:
            if conf.dblp:
                self.card_w_l("DBLP", f"Matched this conference with the {conf.dblp.get('name', '')} (id: <b>{conf.dblp.get('id', '')}</b>) instance on DBLP.", conf.dblp.get('url', ''), "Conference on DBLP")
            else:
                self.card_w_l("DBLP", "No information found on DBLP about this conference.")
        with dfColumns[1]:
            if conf.aida:
                self.card_w_l("AIDA Dashboard", f"Matched this conference with the {conf.aida.get('name', '')} (id: <b>{conf.aida.get('id', '')}</b>) instance on the AIDA Dashboard.", conf.aida.get('url', ''), "Conference on the AIDA Dashboard")
            else:
                self.card_w_l("AIDA Dashboard", "No information found on the AIDA Dashboard about this conference.")
        with dfColumns[2]:
            if conf.confident:
                self.card_w_l("ConfIDent", f"Matched this conference with the {conf.confident.get('name', '')} (id: <b>{conf.confident.get('id', '')}</b>) instance on the Conference ConfIDent.", conf.confident.get('url', ''), "Conference on ConfIDent")
            else:
                self.card_w_l("ConfIDent", "No information found on ConfIDent database about this conference.")

        self.display_topics(conf, filename, storage)
        
        st.divider()
        buffer = BytesIO()
        export_file = conf.name
        
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            organisers_df.to_excel(writer, sheet_name='Organisers', index=True)
            conf_info_df.to_excel(writer, sheet_name='Conference Info', index=True)
            
        st.download_button(
            label="Download data as Excel",
            data=buffer,
            file_name=f"{export_file}.xlsx",
            mime='application/vnd.ms-excel',
        )

    @st.fragment
    def display_topics(self, conf: Conference, filename: str = None, storage = None) -> None:
        if conf.topics and conf.topics.enhanced_topics:
            st.divider()      
            self.add_header("Topics of Interest")
            
            col1, col2 = st.columns([5, 1], vertical_alignment="bottom")
            with col1:
                new_threshold = st.slider("Similarity Threshold (higher is stricter)", min_value=0.0, max_value=1.0, value=conf.topics.preferred_threshold, step=0.05)
            
            with st.spinner("Recomputing topic matches..."):
                conf.topics.match_openalex_topics(sim_threshold=new_threshold)
                
            with col2:
                if st.button("Save this setting!", use_container_width=True):
                    conf.topics.preferred_threshold = new_threshold
                    if filename and storage:
                        loaded_data = storage.load(filename)
                        storage.save(filename, conf.to_dict(), loaded_data.get("llm-output"))
                        st.toast("Settings saved successfully!", icon="✅")
            
            for topic, openalex_topics in conf.topics.enhanced_topics.items():
                line = f"* {topic}"
                if len(openalex_topics) > 0:
                    for oatopic in openalex_topics:
                        if isinstance(oatopic, dict):
                            sim_val = oatopic.get("similarity")
                            line += f" :blue-badge[📎 {oatopic['topic']} (sim: {sim_val:.2f})]"
                        else:
                            line += f" :blue-badge[📎 {oatopic}]"
                st.markdown(line)
