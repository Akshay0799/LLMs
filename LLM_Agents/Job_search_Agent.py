import typer
from typing import Optional,List, Iterator

from pydantic import BaseModel, Field
from phi.assistant import Assistant
from phi.model.google import Gemini
from phi.agent import Agent
from phi.workflow import Workflow, RunResponse, RunEvent
from phi.storage.assistant.postgres import PgAssistantStorage
from phi.knowledge.pdf import PDFUrlKnowledgeBase
from phi.tools.duckduckgo import DuckDuckGo
from phi.vectordb.pgvector import PgVector2
from phi.utils.log import logger
from phi.tools.crawl4ai_tools import Crawl4aiTools
from phi.utils.pprint import pprint_run_response

import os
from dotenv import load_dotenv
load_dotenv()

Gemini.api_key = os.getenv("GOOGLE_API_KEY")
db_url = "postgresql+psycopg://ai:ai@localhost:5532/ai"

knowledge_base=PDFUrlKnowledgeBase(
    urls=["https://phi-public.s3.amazonaws.com/recipes/ThaiRecipes.pdf"],
    vector_db=PgVector2(collection="recipes", db_url=db_url)
)

knowledge_base.load()

storage=PgAssistantStorage(table_name="pdf_assistant", db_url=db_url)

class JobPosting(BaseModel):
    title: str = Field(..., description="Title of the job.position.")
    company: str = Field(..., description="Name of the company the Job posting belongs to")
    location: str = Field(..., description="Region/ Location the job posting")
    level: str = Field(..., description="Level of the designation: Whether it is Entry level, Intermediate or senior or so on")
    description: str = Field(..., description="Job description")
    workMode: str = Field(..., description="Mode of work for the job, whether it is Remote, Hybrid or Inperson always")
    salary: str = Field(..., description="Salary of the job position(if mentioned)")
    yoe: str = Field(..., description="Required years of experience for the job")
    url: str = Field(..., description="Link to the job posting's website")

class JobSearchResults(BaseModel):
    items: list[JobPosting]

class SearchResults(BaseModel):
    items: []

class FindJobPosting(Workflow):
    ## Searcher
    searcher: Agent = Agent(
        model=Gemini(id="gemini-2.0-flash-exp"),
        tools=[DuckDuckGo()],
        knowledge_base=knowledge_base,
        instructions=["Given the information you have from the resume, search through web for job postings that woud be the most relevant to the experience and skills mentioned in the resume, find and return the top 3 websites where it can be purchased from."],
        response_model=SearchResults
    )

    jobScraper: Agent = Agent(
        name="Crawling Agent",
        role="Scrap information off the website and display it",
        model=Gemini(id="gemini-2.0-flash-exp"),
        tools=[Crawl4aiTools(max_length=None)],
        show_tool_calls=True,
        instructions=[
            "1. Given an Job posting website/url, scrap through the website and find details of the different job listings available",
            "2. Present the information in the form of a grid with the the following details - 'Job Title', 'Company Name', 'Location of the job role, Level or designation denoting whether the role is Entry level, Intermediate or senior position, 'Job description', 'Mode of work'(Remote/hybrid/In-person), 'Salary' of the job position(if mentioned), 'years of experience' Required  for the job'Url' of the job posting ",
            "3. Check Product stock availability"
        ],
        response_model = JobSearchResults,
        # structured_outputs=True,
        )

    def run(self, item: str = None, use_cache: bool = True) -> Iterator[RunResponse]:
        # logger.info(f"Fetching the item listings: {item}")
        num_tries = 0
        search_results: Optional[SearchResults] = None
        # Run until we get a valid search results
        while search_results is None and num_tries < 3:
            try:
                num_tries += 1
                searcher_response: RunResponse = self.searcher.run()
                if (
                    searcher_response
                    and searcher_response.content
                    and isinstance(searcher_response.content, SearchResults)
                ):
                    logger.info(f"Searcher found {len(searcher_response.content.items)} results.")
                    # logger.info(f"Searcher response:\n {searcher_response.content.items}")
                    item_list = searcher_response.content.items
                    scraper_response: RunResponse = self.jobScraper.run(item_list[0])
                    logger.info(f"Scraper response:\n {scraper_response.content}")
                    logger.info("Generating Job postings...")
                    return scraper_response
                else:
                    logger.warning("Searcher response invalid, trying again...")
            except Exception as e:
                logger.warning(f"Error running searcher: {e}")

        # If no search_results are found for the topic, end the workflow
        if search_results is None or len(search_results.items) == 0:
            yield RunResponse(
                run_id=self.run_id,
                event=RunEvent.workflow_completed,
                content=f"Sorry, could not find relevant job postings",
            )
    
    
    

item = ""
generate_job_listings =FindJobPosting(
    session_id=f"generate-blog-post-on-{item}",
    # storage=SqlWorkflowStorage(
    #     table_name="generate_blog_post_workflows",
    #     db_file="tmp/workflows.db",
    # ),
)
# Run workflow
job_listing: RunResponse = generate_job_listings.run(item=item)

# Print the response
pprint_run_response(job_listing, markdown=True)
