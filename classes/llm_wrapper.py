import json
from openai import OpenAI
from .call_for_paper import CallForPaper

class LLMWrapper:
    def __init__(self, api_url: str, api_key: str, referer: str = "", title: str = ""):
        self.client = OpenAI(base_url=api_url, api_key=api_key)
        self.extra_headers = {
            "HTTP-Referer": referer,
            "X-Title": title
        }
        self.model = "openai/gpt-4o"

    def prepare_prompt(self, cfp: CallForPaper) -> str:
        text_prompt = f"""In this prompt, you will receive a Call for Papers of a scientific event. Your task is to parse it, and identify some crucial elements.

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
                </call_for_papers>"""
        return text_prompt

    def run_model(self, cfp: CallForPaper) -> dict:
        text_prompt = self.prepare_prompt(cfp)
        
        messages = [{"role": "user", "content": text_prompt}]
        response_format = {
            "type": "json_schema",
            "json_schema": {
              "name": "organising_committe_of_conference",
              "strict": True,
              "schema": {
                "type": "object",
                "properties": {
                  "event_name": {
                    "type": "string",
                    "description": "Name of the workshop or conference. This identifies the extended name of the event."
                  },
                  "conference_series": {
                    "type": "string",
                    "description": "This refers to the name of a conference series, which is a collection of events that happen on a regular basis. It's usually similar to the event_name property, but without the edition number or the year. Also it does not contain the event_acronym."
                  },
                  "event_acronym": {
                    "type": "string",
                    "description": "Acronym of the workshop or conference. This identifies the acronym name of the event."
                  },
                  "colocated_with": {
                    "type": "string",
                    "description": "If the name of the event is co-located with another big event. Otherwise if empty."
                  },
                  "year": {
                    "type": "string",
                    "description": "Year in which the event takes place. The only acceptable format is YYYY, such as 2024."
                  },
                  "location": {
                    "type": "string",
                    "description": "City or location name"
                  },
                  "topics": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    },
                    "description": "A list of topics of interest, research areas, or submission categories mentioned in the Call for Papers."
                  },
                  "organisers": {
                    "type": "array",
                    "items": {
                            "type": "object",
                            "properties": {
                                "organiser_name": {
                                    "type": "string",
                                    "description": "The organiser name."
                                },
                                "organiser_affiliation": {
                                    "type": "string",
                                    "description": "The institution (affiliation) of the organiser. This can be either a university or a company."
                                },
                                "organiser_country": {
                                    "type": "string",
                                    "description": "The institution country of the organiser. This information is not always available."
                                },
                                "track_name": {
                                    "type": "string",
                                    "description": "This identifies the main track in which the organiser is involved. A conference may have several tracks, whereas a workshop may have one single track. As default value you shall use 'main' if there are no tracks."
                                }
                            },
                        "required": ["organiser_name", "organiser_affiliation", "organiser_country", "track_name"],
                        "additionalProperties": False
                        },
                    "description": "Identifies the name, affiliation (ideally including country) of ALL the conference organisers, chairs, and committee members."
                  }
                },
                "required": ["event_name", "event_acronym", "conference_series", "colocated_with", "year", "location", "topics", "organisers"],
                "additionalProperties": False
              }
            }
        }
        
        completion = self.client.chat.completions.create(
            extra_headers=self.extra_headers, 
            model=self.model, 
            messages=messages, 
            response_format=response_format
        )
        
        result = json.loads(completion.choices[0].message.content)
        
        # Post-processing
        tracks = set()
        for org in result.get("organisers", []):
            tracks.add(org.get("track_name", ""))
            
        multi_track = len(tracks) > 1
        if multi_track:
            for org in result.get("organisers", []):
                if org.get("track_name", "").lower() == "main":
                    org["track_name"] = "Other"
                    
        for org in result.get("organisers", []):
            org["affiliation_provenance"] = "LLM"
            org["verified"] = False
            
        return result
