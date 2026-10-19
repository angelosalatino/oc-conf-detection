import streamlit as st
import pandas as pd
from io import BytesIO
import base64
import os
import html
import requests
import pyalex
from pyalex import Works
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
        
        conf_key = filename or getattr(conf, 'acronym', 'default') or 'default'
        audit_state_key = f"audit_results_{conf_key}"
        if audit_state_key not in st.session_state:
            st.session_state[audit_state_key] = None

        audit_dict = st.session_state[audit_state_key]
        if audit_dict is not None:
            # Map combined audit status to organisers_mod: [RW_emoji PB_emoji] with link to Audit_Researchers
            def get_rwpb_value(row):
                name = str(row.get("Name", "")).strip()
                openalex = str(row.get("OpenAlex Profile", "")).strip() if "OpenAlex Profile" in row else ""
                entry = audit_dict.get(openalex) or audit_dict.get(name)
                if not entry or not isinstance(entry, dict):
                    return "—"
                rw = entry.get("rw", "➖")
                pb = entry.get("pb", "➖")
                
                # If OpenAlex Profile is available, format as LinkColumn cell with fragment #emoji emoji 🔗
                if openalex and openalex.startswith("http"):
                    import urllib.parse
                    encoded_id = urllib.parse.quote(openalex, safe="")
                    # Deep-link to Audit_Researchers
                    target_url = f"Audit_Researchers?author_id={encoded_id}"
                    return f"{target_url}#{rw} {pb} 🔗"
                else:
                    return f"#{rw} {pb}"

            organisers_mod["RW-PB"] = organisers_mod.apply(get_rwpb_value, axis=1)

        head_col, toggle_col = st.columns([4, 1], vertical_alignment="bottom")
        with head_col:
            self.add_header("Organisers")
        with toggle_col:
            comprehensive_view = st.toggle("Comprehensive view", value=False, key=f"org_toggle_{conf_key}")
        
        if organisers_mod.empty:
            st.write("No organisers found.")
        else:
            if not comprehensive_view:
                # Simplified view (default): Name (hyperlinked to OpenAlex Profile), Affiliation, Country, Track, [RW-PB]
                simple_df = organisers_mod.copy(deep=True)
                has_openalex = "OpenAlex Profile" in simple_df.columns
                
                # Format Name column: embed name in OpenAlex URL fragment so LinkColumn displays the person's name as a clickable link
                if has_openalex:
                    def make_name_link(row):
                        name = str(row.get("Name", ""))
                        url = row.get("OpenAlex Profile")
                        if pd.notnull(url) and str(url).strip():
                            clean_url = str(url).strip().rstrip("/")
                            return f"{clean_url}#{name}"
                        return name

                    simple_df["Name"] = simple_df.apply(make_name_link, axis=1)

                simple_cols = [c for c in ["Name", "Affiliation", "Country", "Track", "RW-PB"] if c in simple_df.columns]
                df_to_show = simple_df[simple_cols]

                col_cfg = {
                    "Name": st.column_config.LinkColumn(
                        "Name",
                        help="Organiser name (links to OpenAlex Profile if matched)",
                        display_text=r"#(.*)"
                    ),
                }
                if "RW-PB" in df_to_show.columns:
                    col_cfg["RW-PB"] = st.column_config.LinkColumn(
                        "RW-PB",
                        help="RetractionWatch & PubPeer audit. Click 🔗 to open full Researcher Audit profile.",
                        display_text=r"#(.*)"
                    )

                st.dataframe(
                    df_to_show,
                    column_config=col_cfg,
                    width=1920
                )
            else:
                # Comprehensive view: show all available columns from the full in-memory dataframe
                col_cfg = {
                    "ROR": st.column_config.LinkColumn("ROR", display_text=r"https://ror\.org/(.*)"),
                    "OpenAlex Profile": st.column_config.LinkColumn("OpenAlex Profile", display_text=r"https://openalex\.org/(.*)"),
                    "ORCID": st.column_config.LinkColumn("ORCID", display_text=r"https://orcid\.org/(.*)"),
                }
                if "RW-PB" in organisers_mod.columns:
                    col_cfg["RW-PB"] = st.column_config.LinkColumn(
                        "RW-PB",
                        help="RetractionWatch & PubPeer audit. Click 🔗 to open full Researcher Audit profile.",
                        display_text=r"#(.*)"
                    )

                st.dataframe(
                    organisers_mod,
                    column_config=col_cfg,
                    width=1920
                )

            # Audit Organisers action under the dataframe
            audit_btn_col, info_btn_col = st.columns([1, 4], vertical_alignment="center")
            with audit_btn_col:
                run_audit = st.button("Audit Organisers", key=f"btn_audit_orgs_{conf_key}", type="primary", use_container_width=True)
            with info_btn_col:
                if audit_dict is not None:
                    st.caption("ℹ️ Audit complete. **RW** (RetractionWatch: ✅ passed / ⚠️ retracted), **PB** (PubPeer: ✅ passed / 💬 comments found).")
                else:
                    st.caption("Audit all organisers with OpenAlex profiles against the RetractionWatch database and PubPeer post-publication peer review.")

            if run_audit:
                results_map = {}
                openalex_api = st.session_state.get('config', {}).get('OPENALEX', 'openalex_api', fallback='') if 'config' in st.session_state else ''
                pyalex.config.api_key = openalex_api

                progress_text = st.empty()
                progress_bar = st.progress(0)
                total_orgs = len(organisers_mod)

                for idx, (_, row) in enumerate(organisers_mod.iterrows()):
                    name = str(row.get("Name", "")).strip()
                    openalex_url = str(row.get("OpenAlex Profile", "")).strip() if "OpenAlex Profile" in row else ""
                    orcid = str(row.get("ORCID", "")).strip() if "ORCID" in row else ""
                    
                    progress_text.text(f"Auditing organiser {idx + 1} of {total_orgs}: {name}...")
                    
                    if not openalex_url or not openalex_url.startswith("http"):
                        status_entry = {"rw": "➖", "pb": "➖"}
                    else:
                        author_id = openalex_url.split("/")[-1].strip()
                        try:
                            # 1. Fetch publications
                            works = []
                            pager = Works().filter(author={"id": author_id}).paginate(n_max=None)
                            for page in pager:
                                works.extend(page)

                            # Extract DOIs and normalized titles from researcher's publications
                            works_dois = set()
                            for w in works:
                                d = w.get("doi") or ""
                                if d:
                                    if d.startswith("https://doi.org/"):
                                        d = d.replace("https://doi.org/", "")
                                    works_dois.add(d.strip().lower())

                            # 2. RetractionWatch audit (paper level)
                            has_rw = any(w.get("is_retracted") for w in works)
                            if not has_rw and (works_dois or orcid):
                                crossref_url = "https://api.crossref.org/v1/works"
                                params = {"query.author": name, "filter": "update-type:retraction", "rows": 50}
                                if orcid:
                                    clean_orcid = orcid.split("orcid.org/")[-1].strip()
                                    params["filter"] = f"orcid:{clean_orcid},update-type:retraction"
                                try:
                                    r = requests.get(crossref_url, params=params, timeout=8)
                                    if r.status_code == 200:
                                        items = r.json().get("message", {}).get("items", [])
                                        # Verify at work (paper) level: matched DOI in author's works or matching verified ORCID
                                        for item in items:
                                            c_doi = (item.get("DOI") or "").strip().lower()
                                            if c_doi and c_doi in works_dois:
                                                has_rw = True
                                                break
                                            if orcid:
                                                # Check if author array in Crossref actually contains this person's ORCID
                                                for c_auth in item.get("author", []):
                                                    if clean_orcid in (c_auth.get("ORCID") or ""):
                                                        has_rw = True
                                                        break
                                                if has_rw:
                                                    break
                                except Exception:
                                    pass

                            rw_val = "⚠️" if has_rw else "✅"

                            # 3. PubPeer audit
                            has_pb = False
                            dois = list(works_dois)

                            if dois:
                                pubpeer_url = "https://pubpeer.com/v3/publications"
                                try:
                                    resp = requests.post(pubpeer_url, json={"dois": dois, "devkey": "Zotero"}, timeout=8)
                                    if resp.status_code == 200:
                                        feedbacks = resp.json().get("feedbacks", [])
                                        if feedbacks:
                                            has_pb = True
                                except Exception:
                                    pass

                            pb_val = "💬" if has_pb else "✅"
                            status_entry = {"rw": rw_val, "pb": pb_val}
                        except Exception:
                            status_entry = {"rw": "❓", "pb": "❓"}

                    results_map[name] = status_entry
                    if openalex_url:
                        results_map[openalex_url] = status_entry

                    progress_bar.progress((idx + 1) / total_orgs)

                progress_text.empty()
                progress_bar.empty()
                st.session_state[audit_state_key] = results_map
                st.rerun()
        
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
        export_file = conf.name or "conference_data"
        
        # Prepare enhanced Organisers sheet
        export_orgs = organisers_df.copy(deep=True)
        # Rename or ensure clean columns
        if 'verified' in export_orgs.columns:
            export_orgs['Verified Affiliation'] = export_orgs['verified'].apply(lambda x: "Yes" if x is True else "No")
            export_orgs = export_orgs.drop(columns=['verified'])
        
        # If audit results exist in session state, add RetractionWatch and PubPeer columns
        if audit_dict is not None:
            rw_list = []
            pb_list = []
            for _, row in export_orgs.iterrows():
                name = str(row.get("Name", "")).strip()
                openalex = str(row.get("OpenAlex Profile", "")).strip() if "OpenAlex Profile" in row else ""
                entry = audit_dict.get(openalex) or audit_dict.get(name)
                if entry and isinstance(entry, dict):
                    rw_val = entry.get("rw", "➖")
                    pb_val = entry.get("pb", "➖")
                    rw_desc = "Retracted" if rw_val == "⚠️" else ("Clear" if rw_val == "✅" else "Not Audited")
                    pb_desc = "Comments Found" if pb_val == "💬" else ("Clear" if pb_val == "✅" else "Not Audited")
                    rw_list.append(rw_desc)
                    pb_list.append(pb_desc)
                else:
                    rw_list.append("Not Audited")
                    pb_list.append("Not Audited")
            export_orgs["RetractionWatch Status"] = rw_list
            export_orgs["PubPeer Status"] = pb_list

        # Prepare Topics sheet if available
        topics_rows = []
        if conf.topics and hasattr(conf.topics, "enhanced_topics") and conf.topics.enhanced_topics:
            for top, oa_list in conf.topics.enhanced_topics.items():
                if oa_list:
                    for item in oa_list:
                        if isinstance(item, dict):
                            topics_rows.append({
                                "Extracted Topic": top,
                                "OpenAlex Topic": item.get("topic", ""),
                                "Similarity Score": round(float(item.get("similarity", 0.0)), 2)
                            })
                        else:
                            topics_rows.append({
                                "Extracted Topic": top,
                                "OpenAlex Topic": str(item),
                                "Similarity Score": ""
                            })
                else:
                    topics_rows.append({
                        "Extracted Topic": top,
                        "OpenAlex Topic": "None",
                        "Similarity Score": ""
                    })
        elif conf.topics and hasattr(conf.topics, "topics_list") and conf.topics.topics_list:
            for top in conf.topics.topics_list:
                topics_rows.append({
                    "Extracted Topic": top,
                    "OpenAlex Topic": "",
                    "Similarity Score": ""
                })
        topics_df = pd.DataFrame(topics_rows)

        # Prepare Tracks sheet if tracks exist
        tracks_list = []
        if "Track" in organisers_df.columns:
            tracks_list = [t for t in organisers_df["Track"].dropna().unique() if str(t).strip()]
        tracks_df = pd.DataFrame({"Conference Track": tracks_list}) if tracks_list else pd.DataFrame()

        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            workbook = writer.book
            
            # Header formatting: Dark blue #183642 with white text
            header_format = workbook.add_format({
                'bold': True,
                'text_wrap': False,
                'valign': 'vcenter',
                'fg_color': '#183642',
                'font_color': '#FFFFFF',
                'border': 1
            })

            # Data cell format
            cell_format = workbook.add_format({
                'valign': 'vcenter'
            })

            # 1. Conference Summary Sheet
            conf_info_df.to_excel(writer, sheet_name='Conference Summary', index=False)
            ws_summary = writer.sheets['Conference Summary']
            ws_summary.set_row(0, 24, header_format)
            ws_summary.set_column('A:A', 25, cell_format)
            ws_summary.set_column('B:B', 60, cell_format)

            # 2. Organisers Sheet
            export_orgs.to_excel(writer, sheet_name='Organisers', index=False)
            ws_orgs = writer.sheets['Organisers']
            ws_orgs.set_row(0, 24, header_format)
            for idx, col in enumerate(export_orgs.columns):
                max_len = max(
                    export_orgs[col].astype(str).map(len).max() if not export_orgs.empty else 0,
                    len(str(col))
                ) + 4
                ws_orgs.set_column(idx, idx, max(max_len, 14), cell_format)

            # 3. Topics of Interest Sheet
            if not topics_df.empty:
                topics_df.to_excel(writer, sheet_name='Topics of Interest', index=False)
                ws_topics = writer.sheets['Topics of Interest']
                ws_topics.set_row(0, 24, header_format)
                for idx, col in enumerate(topics_df.columns):
                    max_len = max(
                        topics_df[col].astype(str).map(len).max() if not topics_df.empty else 0,
                        len(str(col))
                    ) + 4
                    ws_topics.set_column(idx, idx, max(max_len, 18), cell_format)

            # 4. Tracks Sheet
            if not tracks_df.empty:
                tracks_df.to_excel(writer, sheet_name='Tracks', index=False)
                ws_tracks = writer.sheets['Tracks']
                ws_tracks.set_row(0, 24, header_format)
                ws_tracks.set_column('A:A', 35, cell_format)
            
        st.download_button(
            label="Download data as Excel",
            data=buffer.getvalue(),
            file_name=f"{export_file}.xlsx",
            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            type="primary"
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
