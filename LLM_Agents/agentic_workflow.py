import json
from typing import Optional, Iterator

from pydantic import BaseModel, Field
from phi.model.google import Gemini
from phi.agent import Agent
from phi.workflow import Workflow, RunResponse, RunEvent
from phi.storage.workflow.sqlite import SqlWorkflowStorage
from phi.tools.duckduckgo import DuckDuckGo
from phi.utils.pprint import pprint_run_response
from phi.utils.log import logger
from phi.tools.crawl4ai_tools import Crawl4aiTools
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
Gemini.api_key = os.getenv("GOOGLE_API_KEY")


class Item(BaseModel):
    name: str = Field(..., description="Name of the item.")
    price: str = Field(..., description="Price of the item in CAD.")
    brand: str = Field(..., description="Brand Name of the item.")
    stock: str = Field(..., description="Stock availability of the item")
    description: str = Field(..., description="Brief description of the item.")
    url: str = Field(..., description="Link to the item's website.")

class SearchResults(BaseModel):
    items: list[Item]

class FindItemListing(Workflow):
    ## Crawling Agent
    amazonCrawler: Agent = Agent(
        name="Crawling Agent",
        role="Scrap information off the website and display it",
        model=Gemini(id="gemini-2.0-flash-exp"),
        tools=[Crawl4aiTools(max_length=None)],
        show_tool_calls=True,
        instructions=[
            "1. Given an item listing website, scrap through the website and find the listing of the given product",
            "2. Present the information in the form of a grid with the the following details - Title of the product, Price in CAD, Brand name of the product, Stock Availability, Brief description of the product ",
            "3. Check Product stock availability"
        ],
        response_model = Item,
        # structured_outputs=True,
        )
    
    ## Searcher
    searcher: Agent = Agent(
        model=Gemini(id="gemini-2.0-flash-exp"),
        tools=[DuckDuckGo()],
        instructions=["Given an item name, search the item listing on websites other than Amazon for its purchase and return the top 3 websites where it can be purchased from."],
        response_model=SearchResults
    )

    def run(self, item: str, use_cache: bool = True) -> Iterator[RunResponse]:
        logger.info(f"Fetching the item listings: {item}")

        # Use the cached blog post if use_cache is True
        # if use_cache and "blog_posts" in self.session_state:
        #     logger.info("Checking if cached blog post exists")
        #     for cached_blog_post in self.session_state["blog_posts"]:
        #         if cached_blog_post["topic"] == topic:
        #             logger.info("Found cached blog post")
        #             yield RunResponse(
        #                 run_id=self.run_id,
        #                 event=RunEvent.workflow_completed,
        #                 content=cached_blog_post["blog_post"],
        #             )
        #             return


        ## Step 1: Search Amazon for the item listing adn availability
        # amazon_response: RunResponse = self.amazonCrawler.run("https://www.amazon.ca/"+item)

        # if (
        #             amazon_response
        #             and amazon_response.content
        #             and isinstance(amazon_response.content, Item)
        #         ):
        #     logger.info(f"Amazon Crawler found item listing for {item}")
        #     # logger.info(f"Output from crawler: {amazon_response.content}")
        #     logger.info("Generating Item Listing...")
        #     return amazon_response
        # else:

        # Step 2: Search the web for item listings
        num_tries = 0
        search_results: Optional[SearchResults] = None
        # Run until we get a valid search results
        while search_results is None and num_tries < 3:
            try:
                num_tries += 1
                searcher_response: RunResponse = self.searcher.run(item)
                if (
                    searcher_response
                    and searcher_response.content
                    and isinstance(searcher_response.content, SearchResults)
                ):
                    logger.info(f"Searcher found {len(searcher_response.content.items)} results.")
                    # logger.info(f"Searcher response:\n {searcher_response.content.items}")
                    item_list = searcher_response.content.items
                    crawler_response: RunResponse = self.amazonCrawler.run(item_list[0].url)
                    logger.info(f"Crawler response:\n {crawler_response.content}")
                    logger.info("Generating Item Listing...")
                    return searcher_response
                else:
                    logger.warning("Searcher response invalid, trying again...")
            except Exception as e:
                logger.warning(f"Error running searcher: {e}")

        # If no search_results are found for the topic, end the workflow
        if search_results is None or len(search_results.items) == 0:
            yield RunResponse(
                run_id=self.run_id,
                event=RunEvent.workflow_completed,
                content=f"Sorry, could not find listings of {item}",
            )
            

        # # Step 2: Write a blog post
        # logger.info("Writing blog post")
        # # Prepare the input for the writer
        # writer_input = {
        #     "topic": topic,
        #     "items": [v.model_dump() for v in search_results.items],
        # }
        # # Run the writer and yield the response
        # yield from self.writer.run(json.dumps(writer_input, indent=4), stream=True)

        # # Save the blog post in the session state for future runs
        # if "blog_posts" not in self.session_state:
        #     self.session_state["blog_posts"] = []
        # self.session_state["blog_posts"].append({"topic": topic, "blog_post": self.writer.run_response.content})

item = "Samsung S25"
generate_item_listing =FindItemListing(
    session_id=f"generate-blog-post-on-{item}",
    # storage=SqlWorkflowStorage(
    #     table_name="generate_blog_post_workflows",
    #     db_file="tmp/workflows.db",
    # ),
)
# Run workflow
item_listing: RunResponse = generate_item_listing.run(item=item)

# Print the response
pprint_run_response(item_listing, markdown=True)
