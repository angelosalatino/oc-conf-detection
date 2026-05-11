from .openalex_wrapper import OpenAlexWrapper

class Organisers:
    def __init__(self, organisers_list: list):
        self.organisers_list = organisers_list

    def enrich_with_openalex(self, oa_wrapper: OpenAlexWrapper, year: str):
        self.organisers_list = oa_wrapper.enrich_organisers(self.organisers_list, year)

    def to_dict(self):
        return self.organisers_list
