import pickle
from sentence_transformers import SentenceTransformer

class Topics:
    def __init__(self, topics_list: list):
        self.topics_list = topics_list
        self.enhanced_topics = {}

    def match_openalex_topics(self, debug=False):
        if not self.topics_list:
            return
            
        dist_threshold = 0.6
        
        with open('data_sources/openalex.pickle', 'rb') as handle:
            openalex = pickle.load(handle)
            
        emb_model = SentenceTransformer("all-MiniLM-L6-v2")
            
        for topic in self.topics_list:
            if debug: print(f"----> {topic}")
            
            embeddings = emb_model.encode([topic])
            dists, similar_items = openalex["index"].search(embeddings, k=5)
            matched_topic = []
            for pos, returned_item in enumerate(similar_items[0]): 
                if debug: print(openalex['sentences'][returned_item], f"({dists[0][pos]:.2f})")
                if dists[0][pos] <= dist_threshold:
                    matched_topic.append(openalex['sentences'][returned_item].lower())
            
            self.enhanced_topics[topic] = list(set(matched_topic))

    def to_dict(self):
        return {
            "topics": self.topics_list,
            "enhanced_topics": self.enhanced_topics
        }
