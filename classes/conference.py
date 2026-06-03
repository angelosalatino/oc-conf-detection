import os
os.environ['FAISS_OPT_LEVEL'] = ''  # do this BEFORE importing any faiss library

import pickle
import urllib.parse
# pyrefly: ignore [missing-import]
from rapidfuzz.distance import Levenshtein
from sentence_transformers import SentenceTransformer
from .organisers import Organisers
from .topics import Topics

class Conference:
    def __init__(self, name: str, acronym: str, series: str, colocated: str, year: str, location: str):
        self.name = name
        self.acronym = acronym
        self.series = series
        self.colocated = colocated
        self.year = year
        self.location = location
        self.organisers = None
        self.topics = None
        
        self.dblp = {}
        self.aida = {}
        self.confident = {}

    def set_organisers(self, organisers: Organisers):
        self.organisers = organisers

    def set_topics(self, topics: Topics):
        self.topics = topics

    def match_conference_with_other_datasets(self, debug=False):
        if not self.series:
            return
            
        model = SentenceTransformer("all-MiniLM-L6-v2")
        embeddings = model.encode([self.series])
        
        # DBLP Matching
        with open('data_sources/DBLP.pickle', 'rb') as handle:
            dblp_confs = pickle.load(handle)
        
        D, I = dblp_confs["index"].search(embeddings, k=1)
        if D[0][0] <= 0.4:
            this_conf_dblp = dblp_confs["sentences"][I[0][0]]
            this_acronym_dblp = dblp_confs["confs"][this_conf_dblp]
        else:
            this_conf_dblp = ""
            this_acronym_dblp = ""

        # AIDA Matching
        with open('data_sources/AIDA.pickle', 'rb') as handle:
            aida_confs = pickle.load(handle)
        
        D, I = aida_confs["index"].search(embeddings, k=1)
        if D[0][0] <= 0.4:
            this_conf_aida = aida_confs["sentences"][I[0][0]]
            this_acronym_aida = aida_confs["confs"][this_conf_aida]
        else:
            this_conf_aida = ""
            this_acronym_aida = ""

        # ConfIDent Matching
        with open('data_sources/ConfIDent.pickle', 'rb') as handle:
            confident_confs = pickle.load(handle)
        
        D, I = confident_confs["index"].search(embeddings, k=1)
        if D[0][0] <= 0.4:
            this_conf_confident = confident_confs["sentences"][I[0][0]]
            this_id_confident = confident_confs["confs"][this_conf_confident]
        else:
            this_conf_confident = ""
            this_id_confident = ""
            
        similarity_dblp = Levenshtein.normalized_similarity(this_conf_dblp, self.series)
        similarity_aida = Levenshtein.normalized_similarity(this_conf_aida, self.series)
        similarity_confident = Levenshtein.normalized_similarity(this_conf_confident, self.series)

        # Logic to prioritize the best match
        if similarity_dblp >= max(similarity_aida, similarity_confident) and similarity_dblp > 0:
            self.dblp = {"name": this_conf_dblp, "id": this_acronym_dblp, "url": f"https://dblp.org/streams/conf/{urllib.parse.quote(this_acronym_dblp, safe='')}"}
            if this_acronym_dblp in aida_confs["dblp"]:
                this_conf_aida = aida_confs["dblp"][this_acronym_dblp]
                this_acronym_aida = this_acronym_dblp
                self.aida = {"name": this_conf_aida, "id": this_acronym_aida, "url": f"https://w3id.org/aida/dashboard/cs/conference/{urllib.parse.quote(this_conf_aida, safe='')}"}
            if this_acronym_dblp in confident_confs["dblp_confs"]:
                this_id_confident = confident_confs["dblp_confs"][this_acronym_dblp]
                this_conf_confident = confident_confs["confids"][this_id_confident]
                self.confident = {"name": this_conf_confident, "id": this_id_confident, "url": f"https://www.confident-conference.org/index.php/{urllib.parse.quote(this_id_confident, safe='')}"}

        elif similarity_aida > max(similarity_dblp, similarity_confident):
            if this_acronym_aida in dblp_confs["idsconfs"]:
                this_conf_dblp = dblp_confs["idsconfs"][this_acronym_aida]
                this_acronym_dblp = this_acronym_aida
                self.dblp = {"name": this_conf_dblp, "id": this_acronym_dblp, "url": f"https://dblp.org/streams/conf/{urllib.parse.quote(this_acronym_dblp, safe='')}"}
            self.aida = {"name": this_conf_aida, "id": this_acronym_aida, "url": f"https://w3id.org/aida/dashboard/cs/conference/{urllib.parse.quote(this_conf_aida, safe='')}"}
            if this_acronym_aida in confident_confs["dblp_confs"]:
                this_id_confident = confident_confs["dblp_confs"][this_acronym_aida] # Fix here
                this_conf_confident = confident_confs["confids"][this_id_confident]
                self.confident = {"name": this_conf_confident, "id": this_id_confident, "url": f"https://www.confident-conference.org/index.php/{urllib.parse.quote(this_id_confident, safe='')}"}

        elif similarity_confident > max(similarity_aida, similarity_dblp):
            if this_id_confident in confident_confs["event2dblp"]:
                dblp_id = confident_confs["event2dblp"][this_id_confident]
                if dblp_id in dblp_confs["idsconfs"]:
                    this_conf_dblp = dblp_confs["idsconfs"][dblp_id]
                    this_acronym_dblp = dblp_id
                    self.dblp = {"name": this_conf_dblp, "id": this_acronym_dblp, "url": f"https://dblp.org/streams/conf/{urllib.parse.quote(this_acronym_dblp, safe='')}"}
                if dblp_id in aida_confs["dblp"]:
                    this_conf_aida = aida_confs["dblp"][dblp_id]
                    this_acronym_aida = dblp_id
                    self.aida = {"name": this_conf_aida, "id": this_acronym_aida, "url": f"https://w3id.org/aida/dashboard/cs/conference/{urllib.parse.quote(this_conf_aida, safe='')}"}
            self.confident = {"name": this_conf_confident, "id": this_id_confident, "url": f"https://www.confident-conference.org/index.php/{urllib.parse.quote(this_id_confident, safe='')}"}

    def to_dict(self):
        return {
            "event_name": self.name,
            "event_acronym": self.acronym,
            "conference_series": self.series,
            "colocated_with": self.colocated,
            "year": self.year,
            "location": self.location,
            "DBLP": self.dblp,
            "AIDA": self.aida,
            "ConfIDent": self.confident,
            "organisers": self.organisers.to_dict() if self.organisers else [],
            **(self.topics.to_dict() if self.topics else {"topics": [], "enhanced_topics": {}})
        }
    
    @classmethod
    def from_dict(cls, data: dict):
        conf = cls(
            name=data.get("event_name", ""),
            acronym=data.get("event_acronym", ""),
            series=data.get("conference_series", ""),
            colocated=data.get("colocated_with", ""),
            year=data.get("year", ""),
            location=data.get("location", "")
        )
        conf.dblp = data.get("DBLP", {})
        conf.aida = data.get("AIDA", {})
        conf.confident = data.get("ConfIDent", {})
        
        if "organisers" in data:
            conf.set_organisers(Organisers(data["organisers"]))
        
        if "topics" in data:
            topics = Topics(data["topics"], data.get("preferred_threshold", 0.60))
            topics.enhanced_topics = data.get("enhanced_topics", {})
            conf.set_topics(topics)
            
        return conf
