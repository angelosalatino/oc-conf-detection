import pickle
import re
import spacy
from sentence_transformers import SentenceTransformer

# Load spacy model at module level so it's loaded only once
try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    import subprocess
    import sys
    subprocess.check_call([sys.executable, "-m", "spacy", "download", "en_core_web_sm"])
    nlp = spacy.load("en_core_web_sm")

class Topics:
    def __init__(self, topics_list: list, preferred_threshold: float = 0.60):
        self.topics_list = topics_list
        self.enhanced_topics = {}
        self.preferred_threshold = preferred_threshold
        
        if self.topics_list:
            with open('data_sources/openalex.pickle', 'rb') as handle:
                self.openalex = pickle.load(handle)
            self.emb_model = SentenceTransformer("all-MiniLM-L6-v2")
        else:
            self.openalex = None
            self.emb_model = None

    def extract_subtopics(self, topic: str) -> list:
        # 1. Split by commas and "and"
        parts = [p.strip() for p in re.split(r',\s*(?:and\s+)?|\s+and\s+', topic) if p.strip()]
        
        extracted = []
        for part in parts:
            if len(part.split()) <= 4:
                # Short enough to be a direct concept
                extracted.append(part)
            else:
                # Use spacy to extract noun chunks
                doc = nlp(part)
                for chunk in doc.noun_chunks:
                    # Filter out simple pronouns
                    if chunk.root.pos_ != "PRON":
                        extracted.append(chunk.text)
        
        # fallback if nothing extracted
        if not extracted:
            extracted.append(topic)
            
        return list(set(extracted))

    def match_openalex_topics(self, debug=False, sim_threshold=0.6):
        if not self.topics_list or not self.openalex or not self.emb_model:
            return
            
        for topic in self.topics_list:
            if debug: print(f"----> {topic}")
            
            subtopics = self.extract_subtopics(topic)
            matched_topics_dict = {}
            
            for sub in subtopics:
                if debug: print(f"  Subtopic: {sub}")
                embeddings = self.emb_model.encode([sub])
                dists, similar_items = self.openalex["index"].search(embeddings, k=5)
                for pos, returned_item in enumerate(similar_items[0]): 
                    dist = float(dists[0][pos])
                    sim = 1.0 - dist
                    if debug: print(f"    Match: {self.openalex['sentences'][returned_item]} ({sim:.2f})")
                    if sim >= sim_threshold:
                        oatopic = self.openalex['sentences'][returned_item].lower()
                        if oatopic not in matched_topics_dict or sim > matched_topics_dict[oatopic]:
                            matched_topics_dict[oatopic] = sim
            
            self.enhanced_topics[topic] = [{"topic": k, "similarity": v} for k, v in matched_topics_dict.items()]

    def to_dict(self):
        return {
            "topics": self.topics_list,
            "enhanced_topics": self.enhanced_topics,
            "preferred_threshold": self.preferred_threshold
        }

