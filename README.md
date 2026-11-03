# Conference Organisers and Content Identifier (COCI)

[![Python 3.12+](https://img.shields.io/badge/python-3.12%20%7C%203.13-blue.svg)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/frontend-Streamlit-red.svg)](https://streamlit.io/)
[![MongoDB](https://img.shields.io/badge/database-MongoDB-green.svg)](https://www.mongodb.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

The **Conference Organisers and Content Identifier (COCI)** is an AI-powered system designed to automate the extraction, semantic enrichment, exploration, and integrity audit of academic **Call for Papers (CfPs)**, conference metadata, and scientific organising committees.

By combining modern Large Language Models (LLMs), semantic vector similarity (FAISS & SentenceTransformers), and authoritative scholarly registries (OpenAlex, DBLP, AIDA Dashboard, and ConfIDent), COCI transforms unstructured text into structured, searchable, and verified knowledge graphs.

---

## Table of Contents

- [Conference Organisers and Content Identifier (COCI)](#conference-organisers-and-content-identifier-coci)
  - [Table of Contents](#table-of-contents)
  - [Core Features](#core-features)
  - [Key Data Extracted](#key-data-extracted)
    - [Conference Metadata](#conference-metadata)
    - [Organiser Details](#organiser-details)
  - [Integrations and Knowledge Mapping](#integrations-and-knowledge-mapping)
    - [OpenAlex Profile Matching \& Verification](#openalex-profile-matching--verification)
    - [Semantic Topic Modeling \& FAISS Indexing](#semantic-topic-modeling--faiss-indexing)
    - [External Registries (DBLP, AIDA, ConfIDent)](#external-registries-dblp-aida-confident)
    - [Research Integrity Auditing (RetractionWatch \& PubPeer)](#research-integrity-auditing-retractionwatch--pubpeer)
  - [Storage Engines and Schema](#storage-engines-and-schema)
    - [Dual/Hybrid Storage Architecture](#dualhybrid-storage-architecture)
    - [Intelligent Metadata Merging Logic](#intelligent-metadata-merging-logic)
  - [Organiser Matching Process](#organiser-matching-process)
  - [Application Portal Modules](#application-portal-modules)
  - [Database Management CLI Utilities](#database-management-cli-utilities)
  - [Getting Started](#getting-started)
    - [Prerequisites](#prerequisites)
    - [Installation](#installation)
    - [Configuration (`config.ini`)](#configuration-configini)
    - [Running the Application](#running-the-application)
  - [LLM Extraction Prompt](#llm-extraction-prompt)
  - [The Team \& Acknowledgements](#the-team--acknowledgements)

---

## Core Features

* **Automated CFP Parsing**: Extracts full conference details, year, location, co-locations, tracks, organising committees, and call topics from raw text.
* **Three Processing Execution Modes**: Support for **Cached** (instant retrieval), **Mild Force** (reuses LLM extraction, re-runs database and vector matching), and **Force** (full top-to-bottom recomputation).
* **Multi-CFP Merging & Deduplication**: Intelligently aggregates multiple Calls for Papers for the same event and year, maintaining raw CFP history and merging committee members and topics.
* **Semantic Vector Topic Filtering**: High-dimensional semantic embeddings with interactive similarity threshold filtering against the OpenAlex topic taxonomy.
* **Academic Integrity Auditing**: Real-time screening of researcher bibliographies against **Retraction Watch** (paper-level and ORCID verification) and **PubPeer** community review discussions.
* **Multi-Sheet Formatted Excel Export**: Downloads structured `.xlsx` workbooks containing conference summaries, audited organisers, topics, and tracks.
* **Comprehensive Analytics Dashboard**: Macro-level database statistics, yearly distributions, series rankings, country demographics, and linked open data coverage.

---

## Key Data Extracted

### Conference Metadata
- **`event_name`**: Full official title of the conference or workshop.
- **`conference_series`**: Recurring series name, normalized without edition or year.
- **`event_acronym`**: Official acronym (e.g., "ISWC", "K-CAP").
- **`colocated_with`**: Parent or co-located conference details.
- **`year`**: Scheduled calendar year.
- **`location`**: Host city and country.
- **`topics`**: List of scientific areas and research topics extracted from the CFP.
- **`enhanced_topics`**: Semantic OpenAlex topics mapped with cosine similarity scores.

### Organiser Details
Each individual in the committee is structured with:
- **`organiser_name`**: Full name of the committee member.
- **`organiser_affiliation`**: Stated academic institution or industry organisation. Verified affiliations cross-referenced with publication history are marked with a verification badge (✪).
- **`organiser_country`**: Canonical, full-form country name (standardized via `country_converter`, e.g., "United States", "United Kingdom", "Netherlands").
- **`track_name`**: Specific conference track or committee role (e.g., "General Chair", "Research Track", "Workshop Chair").
- **`affiliation_ror`**: Research Organization Registry (ROR) persistent identifier.
- **`openalex_page` / `openalex_name`**: Matched OpenAlex author profile identifier and display name.
- **`orcid`**: Verified ORCID identifier.

---

## Integrations and Knowledge Mapping

### OpenAlex Profile Matching & Verification
Organisers are cross-referenced against OpenAlex to identify global scholarly records:
1. **Quality Check**: Rejects homogeneous or default affiliations to prevent false positive matches.
2. **Institutional & Name Search**: Queries authors by institution first; falls back to Levenshtein fuzzy matching on alternative author names and publication counts.
3. **Affiliation Verification**: Validates stated affiliations against recent publication records. Verified matches are assigned a `verified: true` flag (✪).
4. **Identifier Extraction**: Enriches profiles with ROR and ORCID persistent URIs.

### Semantic Topic Modeling & FAISS Indexing
Extracted scientific topics are standardized to avoid keyword fragmentation:
1. Topics are transformed into dense vector embeddings using `SentenceTransformer`.
2. High-dimensional vector search queries a local **FAISS index** containing standardized OpenAlex research topics.
3. An interactive **Similarity Threshold** slider in the UI enables real-time filtering with instant persistence to database records.

### External Registries (DBLP, AIDA, ConfIDent)
Conferences are matched against persistent external academic indexes:
* **DBLP Computer Science Bibliography**: Links to official proceedings and historic publication volumes.
* **AIDA Dashboard**: Provides industry-academia collaborative metrics.
* **Conference ConfIDent**: Provides persistent event IDs and registry verification.

### Research Integrity Auditing (RetractionWatch & PubPeer)
COCI incorporates built-in scientific integrity auditing:
* **Cursor-Based Publication Fetch**: Downloads a researcher's complete bibliography from OpenAlex.
* **RetractionWatch Audits**: Scans publication DOIs and queries the Crossref update API (`update-type:retraction`), verified strictly at the individual paper (DOI) and author ORCID level to eliminate false positives.
* **PubPeer Discussion Checks**: Queries the PubPeer API in batch requests, providing direct links to post-publication peer review comments and discussion threads.
* **In-Event Committee Screening**: The **Audit Organisers** button screens all committee members in an event, displaying a visual `RW-PB` status summary (`✅` passed, `⚠️` retraction found, `💬` comments found) with deep-links to full researcher audit profiles.

---

## Storage Engines and Schema

### Dual/Hybrid Storage Architecture
Configured via `config.ini` (`type = file | mongodb | both`):
- **File Storage**: Saves individual conference JSON files under `processed_cfps/`.
- **MongoDB Storage**: Persists data across two collections:
  1. **`events`**: Contains the full document: progressive integer index (`_id`), array of source file stems (`filenames`), parallel array of raw CFP texts (`cfps`), raw `llm-output`, enriched `processed` schema, and ISO timestamps.
  2. **`events_index`**: High-speed index tracking `index`, `event_name`, `conference_series`, and `year` with compound unique constraints.
- **Hybrid Storage**: Concurrently writes to both local JSON files and MongoDB.

### Intelligent Metadata Merging Logic
When a Call for Papers for an already existing conference and year is processed:
- **Parallel CFP History**: The new file stem is added to `filenames` and the raw text is appended to `cfps`, preserving provenance across multiple call updates or track cycles.
- **Committee Deduplication**: Organisers are matched by ORCID, OpenAlex page, or normalized name. Existing records are enriched with missing fields and verified statuses are preserved.
- **Topic Consolidation**: Merges topic keyword lists and retains the higher similarity score for mapped semantic OpenAlex topics.
- **Registry Links**: Merges external links without overwriting existing mappings.

---

## Organiser Matching Process

```
                      +-----------------------------+
                      |   Extracted Organiser from  |
                      |     Call for Papers text    |
                      +--------------+--------------+
                                     |
                                     v
                      +-----------------------------+
                      |  Affiliation Diversity Check|
                      +--------------+--------------+
                                     |
                  +------------------+------------------+
                  |                                     |
     (Has Valid Affiliation)               (No / Low-Quality Affiliation)
                  |                                     |
                  v                                     v
   +------------------------------+     +-------------------------------+
   |   Search OpenAlex Authors    |     |    Search OpenAlex Authors    |
   |    filtered by Institution   |     |         by Name Only          |
   +--------------+---------------+     +---------------+---------------+
                  |                                     |
          (Match Found?)                        (Multiple Matches?)
           /          \                                 |
        (Yes)         (No)                              v
         /              \               +-------------------------------+
        v                v              |  Fuzzy Match Alternative Names|
+---------------+  +------------+       |   Ranked by Publication Count |
| Verify Recent |  | Fallback to|       +---------------+---------------+
| Publications  |  | Name Search|                       |
+-------+-------+  +-----+------+                       |
        |                |                              |
        +----------------+------------------------------+
                                 |
                                 v
                 +-------------------------------+
                 |  Enrich ORCID, ROR, OpenAlex  |
                 |   Canonical Country Full Form |
                 +-------------------------------+
```

A detailed graphical flowchart is available at [`assets/images/flowchart.png`](assets/images/flowchart.png).

---

## Application Portal Modules

COCI is organized into 5 primary interactive modules accessible via the Hub landing page and sidebar:

1. **Add Events**: Upload plain `.txt` Call for Papers files. Select **Cached**, **Mild Force**, or **Force** execution modes. Features a tabbed display for structured results and an interactive **Read Call for Papers** viewer with an in-place **🔄 Rerun Process** popover.
2. **Explore Events**: Fuzzy search stored events by title, acronym, series, or research topics. Enforces a strict **60% relevance match filter**, highlights matched topics with lightbulb badges, and includes an *"I'm feeling lucky"* quick browser.
3. **Search Organiser**: Aggregates unique organisers database-wide. Features dual-tab profiles displaying an organiser's historical conferences and an on-demand **Researcher Audit**.
4. **Audit Researcher**: Dedicated research integrity tool. Queries OpenAlex author profiles, downloads complete publication bibliographies, and conducts automated **RetractionWatch** and **PubPeer** checks. Supports direct URL deep-linking (`?author_id=...`).
5. **Database Statistics**: Macro-analytics dashboard displaying total conferences, unique scholars, distribution of events per year, top series, country demographics, and external dataset matching coverage (**DBLP**, **AIDA**, **ConfIDent**).

---

## Database Management CLI Utilities

A complete suite of database maintenance tools is provided in `service/db_utilities/`:

* **Export Database**:
  ```bash
  python service/db_utilities/export_mongodb.py --output coci_backup.json.gz
  ```
* **Import Database**:
  ```bash
  python service/db_utilities/import_mongodb.py coci_backup.json.gz --drop --force
  ```
* **Batch Import Processed CFPs Folder**:
  ```bash
  python service/db_utilities/import_processed_cfps.py --folder service/processed_cfps
  ```
* **Batch Country Standardization**:
  Standardizes country names across all database records to full canonical form with automated pre-run backup:
  ```bash
  # Preview transformations safely
  python service/db_utilities/standardize_countries.py --dry-run

  # Apply standardization to MongoDB and local JSON files
  python service/db_utilities/standardize_countries.py --folder service/processed_cfps
  ```

---

## Getting Started

### Prerequisites
* Python 3.12 or 3.13
* MongoDB instance (optional, required for MongoDB/hybrid storage modes):
  ```bash
  brew services start mongodb-community
  ```

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/angelosalatino/oc-conf-detection.git
   cd oc-conf-detection
   ```

2. Create and activate a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. Install required packages:
   ```bash
   pip install -r requirements.txt
   ```

### Configuration (`config.ini`)
Copy `config_sample.ini` to `config.ini` in the root directory:
```bash
cp config_sample.ini config.ini
```

Configure your API keys and storage parameters:
```ini
[DEFAULT]
api_url = https://openrouter.ai/api/v1
api_key = YOUR_OPENROUTER_OR_OPENAI_KEY
model = openai/gpt-4o

[OPENALEX]
openalex_api = YOUR_OPENALEX_API_KEY

[APP]
app_name = Conference Organisers and Content Identifier
app_acronym = COCI

[FOLDERS]
destination_folder = processed_cfps

[TEAM]
email = your.email@example.ac.uk
website = https://your-lab-website.org
description = Your Research Group

[STORAGE]
# Options: file, mongodb, both
type = both

[MONGODB]
uri = mongodb://localhost:27017/
db_name = coci
```

### Running the Application
Launch the Streamlit portal:
```bash
streamlit run COCI.py
```

---

## LLM Extraction Prompt

Below is the core system prompt utilized by the orchestrator to extract structured entities from Call for Papers texts:

```text
In this prompt, you will receive a Call for Papers of a scientific event. Your task is to parse it, and identify some crucial elements.

You must be exhaustive when extracting people. Extract **ALL** organisers, chairs, committee members, and track chairs listed in the text. Do not leave anyone out.

For each person extracted:
- 'organiser_name': The full name.
- 'organiser_affiliation': The institution or company.
- 'organiser_country': The country of the institution (infer if necessary/possible).
- 'track_name': The specific role (e.g., 'General Chair', 'Program Chair') or the track they are associated with (e.g., 'Research Track', 'Demo Track'). If they are part of the general Program Committee, use 'Program Committee'.

Extract:
- the event name and its acronym;
- the conference series;
- any co-located events;
- the year of the event;
- the location of the event;
- the list of topics of interest;
- the list of all organisers/people.

<call_for_papers>
{cfp.text}
</call_for_papers>
```


---

## The Team & Acknowledgements

Developed by the **[Knowledge Media Institute (KMi)](https://kmi.open.ac.uk/)** of **The Open University** in collaboration with **Springer Nature**.

For inquiries or contributions, please contact:
* **Angelo Salatino** — `angelo.salatino@open.ac.uk`
