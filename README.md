# Conference Organising Committee Identifier
 
 The **Conference Organising Committee Identifier** is a powerful, AI-driven tool designed to streamline the process of extracting critical information from academic **Call for Papers (CfPs)**. This tool automates the tedious task of manually parsing documents to identify conference details, series, locations, and, most importantly, the organising committee members.
 
 By using cutting-edge AI technology, this tool saves researchers and administrators countless hours, allowing them to quickly access and analyse key data points about academic events and their organisers. The tool works by taking a CfP as input and outputting a structured JSON object, making the data easily searchable, shareable, and integrable with other systems.
 
 ---
 
 ### Key Data Extracted
 
 The tool is built to recognise and extract the following core components from a CfP:
 
 - **`event_name`**: The full, official title of the conference or workshop.
 - **`conference_series`**: The name of the recurring conference series, without the year or edition number.
 - **`event_acronym`**: The short, official acronym for the event (e.g., "ICML," "CHI").
 - **`colocated_with`**: If the event is held in conjunction with another larger event, this field captures that information.
 - **`location`**: The specific city or location where the event is scheduled to take place.
 - **`organisers`**: An array of objects, each containing detailed information about a committee member.
 
 ---
 
 ### Organiser Details
 
 Within the `organisers` array, the tool provides a rich set of information for each individual:
 
 - **`organiser_name`**: The full name of the organiser.
 - **`organiser_affiliation`**: The academic institution or company the organiser is affiliated with.
 - **`organiser_country`**: The country of the organiser's affiliation, if available.
 - **`track_name`**: The specific track or area of the conference the organiser is involved in. For single-track events, the default value is 'main'.
 
 ### Integration and Data Mapping
 
 To further enrich the extracted information, the **Conference Organising Committee Identifier** integrates with several well-known academic databases.
 
 - **OpenAlex**: Organiser names are mapped to OpenAlex, a global, open index of scholarly literature and researchers. This allows the tool to identify additional identifiers like **ORCIDs** and **RORs** (Research Organisation Registry identifiers) for institutions.
 - **DBLP, AIDA Dashboard, and Conference ConfIDent**: Conference details are mapped to these databases to provide a comprehensive view of the event's history and relevance within the scientific community.
 
 ---

