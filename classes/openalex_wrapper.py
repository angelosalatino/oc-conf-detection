from pyalex import Authors, Institutions
from rapidfuzz.distance import Levenshtein
from rapidfuzz import fuzz
import country_converter as coco

class OpenAlexWrapper:
    def __init__(self, debug=False):
        self.debug = debug
        self.priority_types = {
            "education": 0, "company": 1, "facility": 2, 
            "healthcare": 3, "funder": 4, "government": 5, 
            "archive": 6, "other": 7
        }

    def enrich_organisers(self, organisers: list, year: str) -> list:
        if year is None: 
            year_int = 2026
        else: 
            year_int = int(year)
        
        to_clean = False
        list_of_institutions = []
        for organiser in organisers:
            list_of_institutions.append(organiser.get("organiser_affiliation", ""))
        
        if len(list_of_institutions) >= len(set(list_of_institutions)) * 4 and len(list_of_institutions) > 0:
            to_clean = True
            
        if to_clean:
            for organiser in organisers:
                organiser["organiser_affiliation"] = ""
                organiser["organiser_country"] = ""
                organiser["affiliation_ror"] = ""
                organiser["affiliation_provenance"] = ""
                
        for organiser in organisers:
            if organiser.get("affiliation_provenance") == "OA":
                organiser["organiser_affiliation"] = ""
                organiser["organiser_country"] = ""
                
            organiser["openalex_name"] = ""
            organiser["openalex_page"] = ""
            organiser["orcid"] = ""
            organiser["affiliation_ror"] = ""
            organiser["affiliation_provenance"] = ""
            organiser["verified"] = False

            if self.debug:
                print("+++++++++++++++++++++++++++++++++++++++++++++++++++++++")
                print(organiser)
            
            find_author_with_less_info = False
            openalex_matched_organiser = dict()
            
            # Attempt 1: Search using Institution + Author Name
            if len(organiser.get("organiser_affiliation", "")) > 0:
                if self.debug: print(f"Found {len(organiser['organiser_affiliation'])} affiliations")
                insts = Institutions().search(organiser["organiser_affiliation"]).get()
                if len(insts) > 0:
                    inst_id = insts[0]["id"].replace("https://openalex.org/", "")
                    auths = Authors().search(organiser["organiser_name"]).filter(affiliations={"institution":{"id": inst_id}}).get()
                    if len(auths) > 0:        
                        if self.debug: print(f"{len(auths)} search results found for the author")
                        openalex_matched_organiser = auths[0]
                    else:
                        find_author_with_less_info = True
                        if self.debug: print(f"For {organiser['organiser_name']} I could not find a record")
                else:
                    find_author_with_less_info = True
                    if self.debug: print(f"For {organiser['organiser_name']} I could not find a record of their institution")
            else:
                find_author_with_less_info = True
                if self.debug: print(f"For {organiser['organiser_name']} there is no affiliation")
        
            # Attempt 2: Search for authors without institution info
            if find_author_with_less_info:
                auths = Authors().search(organiser['organiser_name']).get()
                if len(auths) == 1:
                    openalex_matched_organiser = auths[0]
                elif len(auths) == 0:
                    if self.debug: print(f"For {organiser['organiser_name']} I could not find a record, AGAIN")
                else:
                    if self.debug: print(f"Found multiple records for {organiser['organiser_name']}")
                    new_auths = sorted(auths, key=lambda item: item['works_count'], reverse=True)
        
                    max_similarity = 0
                    final_position = -1
                    for author_position, new_auth in enumerate(new_auths):
                        all_alternative_names = new_auth["display_name_alternatives"]
                        for alternative_name in all_alternative_names:
                            author_similarity = Levenshtein.normalized_similarity(alternative_name, organiser['organiser_name'])
                            if author_similarity > max_similarity:
                                if self.debug: print(f"{alternative_name}; {author_position}; {author_similarity}")
                                max_similarity = author_similarity
                                final_position = author_position
                    if final_position != -1:
                        openalex_matched_organiser = new_auths[final_position]
                    
            if len(openalex_matched_organiser) > 0:
                organiser["openalex_name"] = openalex_matched_organiser["display_name"]
                organiser["openalex_page"] = openalex_matched_organiser["id"]
                organiser["orcid"] = ""
                
                if openalex_matched_organiser.get("orcid") is not None:
                    organiser["orcid"] = openalex_matched_organiser["orcid"]
                else:
                    if "orcid" in openalex_matched_organiser.get("ids", {}) and openalex_matched_organiser["ids"]["orcid"] is not None:
                        organiser["orcid"] = openalex_matched_organiser["ids"]["orcid"]
                
                # Case A: No valid affiliation from LLM
                if organiser.get("organiser_affiliation", "") == "": 
                    affiliations = openalex_matched_organiser.get("affiliations", [])
                    if self.debug: print(f"Found {len(affiliations)} affiliations (FOR THIS AUTHOR I DON'T HAVE CLEAR AFFILIATION)")
                    if affiliations and len(affiliations) > 0:
                        affiliations_dict = dict()
                        for institution_position, affiliation in enumerate(affiliations):
                            affiliations_dict[institution_position] = {
                                "pos": institution_position, 
                                "display_name": affiliation["institution"]["display_name"],
                                "type_priority": self.priority_types[affiliation["institution"]["type"]] if affiliation["institution"]["type"] in self.priority_types else 99, 
                                "min_years": min([abs(year_int - i) for i in affiliation["years"]]),
                                "activity": len(affiliation["years"])
                            }
                            
                        sorted_affiliation_history = sorted(affiliations_dict, key=lambda k: (affiliations_dict[k]["min_years"], affiliations_dict[k]["type_priority"]))
                        
                        if affiliations_dict[sorted_affiliation_history[0]]["min_years"] <= 10:
                            most_appropriate_affiliation = affiliations[sorted_affiliation_history[0]]
                            organiser["organiser_affiliation"] = most_appropriate_affiliation["institution"]["display_name"]
                            organiser["affiliation_ror"] = most_appropriate_affiliation["institution"].get("ror", "")
                            organiser["affiliation_provenance"] = "OA"
                            try:
                                organiser["organiser_country"] = coco.convert(names=[most_appropriate_affiliation["institution"]["country_code"]], to='name_short') 
                            except:
                                organiser["organiser_country"] = ""
                
                # Case B: Affiliation exists (from LLM)
                elif len(organiser.get("organiser_affiliation", "")) > 0: 
                    if organiser.get("affiliation_ror", "") == "":
                        max_similarity = 0
                        final_position = -1
                        affiliations = openalex_matched_organiser.get("affiliations", [])
                        if self.debug: print(f"Found {len(affiliations)} affiliations (FOR THIS AUTHOR I ALREADY HOLD INFO ABOUT AFFILIATION)")
                        
                        for institution_position, affiliation in enumerate(affiliations):
                            institution_similarity = fuzz.token_set_ratio(affiliation["institution"]["display_name"], organiser["organiser_affiliation"])
                            if self.debug: print(f'{affiliation["institution"]["display_name"]}; {institution_position}; {institution_similarity}')
                            if institution_similarity > max_similarity:
                                max_similarity = institution_similarity
                                final_position = institution_position
                        
                        if max_similarity >= 40 and final_position != -1:        
                            organiser_institution_from_OA = affiliations[final_position]["institution"]
                            organiser["affiliation_ror"] = organiser_institution_from_OA.get("ror", "")
                            organiser["verified"] = True
                    
        if self.debug: print("---------FINISHED ORGANISERS----------------")
        return organisers
