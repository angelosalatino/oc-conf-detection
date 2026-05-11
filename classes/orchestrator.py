from .call_for_paper import CallForPaper
from .llm_wrapper import LLMWrapper
from .openalex_wrapper import OpenAlexWrapper
from .organisers import Organisers
from .topics import Topics
from .conference import Conference

class Orchestrator:
    def __init__(self, api_url: str, api_key: str, referer: str = "", title: str = ""):
        self.llm_wrapper = LLMWrapper(api_url, api_key, referer, title)
        self.openalex_wrapper = OpenAlexWrapper(debug=False)

    def process(self, cfp_text: str, progress_callback=None, cached_llm_result=None) -> Conference:
        def log(msg):
            print(msg)
            if progress_callback:
                progress_callback(msg)

        cfp = CallForPaper(cfp_text)
        cfp.clean()

        if cached_llm_result:
            log("Using cached LLM results (Mild Force)...")
            llm_result = cached_llm_result
        else:
            log("Connected to remote model. Running model...")
            llm_result = self.llm_wrapper.run_model(cfp)
            log("Finished running model.")

        conf = Conference(
            name=llm_result.get("event_name", ""),
            acronym=llm_result.get("event_acronym", ""),
            series=llm_result.get("conference_series", ""),
            colocated=llm_result.get("colocated_with", ""),
            year=llm_result.get("year", ""),
            location=llm_result.get("location", "")
        )

        organisers = Organisers(llm_result.get("organisers", []))
        log("Processing organisers via OpenAlex...")
        organisers.enrich_with_openalex(self.openalex_wrapper, conf.year)
        conf.set_organisers(organisers)
        log("Completed processing organisers via OpenAlex.")

        topics = Topics(llm_result.get("topics", []))
        log("Mapping the topics of interest to OpenAlex Topics...")
        topics.match_openalex_topics()
        conf.set_topics(topics)
        log("Mapped the topics of interest to OpenAlex Topics.")

        log("Mapping the conference to other datasets...")
        conf.match_conference_with_other_datasets()
        log("Mapped the conference to other datasets.")

        return conf
