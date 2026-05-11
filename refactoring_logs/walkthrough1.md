# Refactoring COCI into an Object-Oriented Architecture

I have successfully restructured the COCI application into a more modular, object-oriented architecture. This decouples the core logic from Streamlit, allowing for headless execution and better testability.

## Changes Made

- Created a new directory `classes/` containing the core logic:
  - `call_for_paper.py`: Encapsulates the Call for Papers text and any future cleaning logic.
  - `llm_wrapper.py`: Connects to OpenRouter and processes the prompt.
  - `openalex_wrapper.py`: Connects to PyAlex and performs matching logic.
  - `organisers.py`: Encapsulates the list of organizers and relies on `OpenAlexWrapper` for enrichment.
  - `topics.py`: Maps the conference topics to OpenAlex concepts using semantic search.
  - `conference.py`: A `Conference` class that holds all metadata, coordinates the logic for matching against DBLP/AIDA/ConfIDent, and ties `Organisers` and `Topics` together.
  - `visualiser.py`: Contains all the Streamlit specific UI rendering functions.
  - `orchestrator.py`: The `Orchestrator` runs the whole pipeline end-to-end, taking a raw text string and returning a fully populated `Conference` object.
- Replaced the old `COCI.py` with `app.py`, which is now much cleaner and just calls the `Orchestrator` and `Visualiser`.
- Created `test_script.py` for headless execution. It loads a CFP from a file, runs it through the orchestrator, and saves the output as a JSON file.
- Moved `COCI.py`, `visual_utilities.py`, and `functionalities.py` to the `old_code/` folder.

## Verification

> [!NOTE]
> The python dependencies for `test_script.py` couldn't be loaded within the active terminal, so be sure to use the virtual environment you normally use when testing it headlessly.

1. You can start the app as usual via Streamlit using the new entrypoint: `streamlit run app.py`
2. You can test a single file headlessly with: `python test_script.py cfps/iswc2025.txt`
