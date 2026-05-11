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
    def __init__(self, topics_list: list):
        self.topics_list = topics_list
        self.enhanced_topics = {}

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

    def match_openalex_topics(self, debug=False, dist_threshold=0.4):
        if not self.topics_list:
            return
        
        with open('data_sources/openalex.pickle', 'rb') as handle:
            openalex = pickle.load(handle)
            
        emb_model = SentenceTransformer("all-MiniLM-L6-v2")
            
        for topic in self.topics_list:
            if debug: print(f"----> {topic}")
            
            subtopics = self.extract_subtopics(topic)
            matched_topic = []
            
            for sub in subtopics:
                if debug: print(f"  Subtopic: {sub}")
                embeddings = emb_model.encode([sub])
                dists, similar_items = openalex["index"].search(embeddings, k=5)
                for pos, returned_item in enumerate(similar_items[0]): 
                    if debug: print(f"    Match: {openalex['sentences'][returned_item]} ({dists[0][pos]:.2f})")
                    if dists[0][pos] <= dist_threshold:
                        matched_topic.append(openalex['sentences'][returned_item].lower())
            
            self.enhanced_topics[topic] = list(set(matched_topic))

    def to_dict(self):
        return {
            "topics": self.topics_list,
            "enhanced_topics": self.enhanced_topics
        }

