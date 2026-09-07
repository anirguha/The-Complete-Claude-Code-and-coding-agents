import os

from dotenv import load_dotenv
from pydantic import BaseModel, Field

from agents import Agent

load_dotenv()
OPENAI_MODEL = os.getenv("DEFAULT_MODEL", "gpt-5.4-nano")
HOW_MANY_SEARCHES = os.getenv("HOW_MANY_SEARCHES", 5)


class WebSearchItem(BaseModel):
    reason: str = Field(description="Provide reasoning why this search is important to the query")
    query: str = Field(description="The search term to use for the web search")


class WebSearchPlan(BaseModel):
    searches: list[WebSearchItem] = Field(description="List of web search results")


INSTRUCTIONS = f"""
You are a research assistant. Given a user query, come up with a set of web searches
to perform to best answer the query. Output {HOW_MANY_SEARCHES} terms to query for.
"""

planner_agent = Agent(
    name="Planner Agent", instructions=INSTRUCTIONS, model=OPENAI_MODEL, output_type=WebSearchPlan
)
