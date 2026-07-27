# Implementation Plan - "Process Organisers" Page

This plan details the implementation of a new page, "Process Organisers", allowing users to search and match academic profiles on OpenAlex, retrieve their publications, and verify if they have any retractions (Retraction Watch via OpenAlex/Crossref) or discussions (PubPeer).

## User Review Required

> [!IMPORTANT]
> - **OpenAlex API key**: Querying OpenAlex requires the API key configured under `[OPENALEX]` in `config.ini` to avoid rate limiting.
> - **PubPeer POST API**: We will call PubPeer's `https://pubpeer.com/v3/publications` POST endpoint with the list of DOIs and the `"Zotero"` devkey, which resolves successfully without a custom developer account.
> - **Retraction Watch Database**:
>   - We will cross-reference publications against OpenAlex's `is_retracted` boolean flag.
>   - We will also execute a secondary search on the Crossref REST API using the author's ORCID or name with the `update-type:retraction` filter to fetch any retracted articles.

## Proposed Changes

### New Streamlit Page

#### [NEW] [6_Process_Organisers.py](file:///Users/aas358/Development/oc-conf-detection/pages/6_Process_Organisers.py)
We will create a new file `pages/6_Process_Organisers.py` containing:
- **Profile Search Interface**:
  - Centered text input to search for a person's name on OpenAlex.
  - Lists matched profiles from OpenAlex with their name, last known institution, works count, and citation count.
  - A "Select Profile" button to initiate checks.
- **Analysis View**:
  - Once a profile is selected:
    - Fetches the author's publications from OpenAlex.
    - **Retraction Watch Check**:
      - Inspects retrieved works for `is_retracted == True`.
      - Queries Crossref API with `filter=update-type:retraction` and the author's name/ORCID.
      - Displays results with warning alerts if any are retracted.
    - **PubPeer Comments Check**:
      - Extracts DOIs and batch queries PubPeer's POST API.
      - Displays papers that have comments on PubPeer along with comment counts, timestamps, and direct links to the discussions.

---

## Verification Plan

### Automated Verification
We will verify that the new file compiles successfully:
`python -m py_compile pages/6_Process_Organisers.py`

### Manual Verification
1. Run the Streamlit application `streamlit run COCI.py`.
2. Navigate to "Process Organisers".
3. Search for a well-known researcher (e.g. `"Didier Raoult"`).
4. Verify that:
   - Profile matches are displayed.
   - Selecting a profile fetches publications.
   - Retracted papers are successfully detected and listed under the Retraction Watch section.
   - Papers with comments on PubPeer are successfully detected and listed with their comments count.
