import os

from agents.model_settings import ModelSettings
from dotenv import load_dotenv

from agents import Agent, WebSearchTool

load_dotenv()
OPENAI_MODEL = os.getenv("DEFAULT_MODEL", "gpt-5.4-nano")

INSTRUCTIONS = """
You are a research assistant. Given a search term, you search the web for that term and 
produce a concise summary of the results. The summary must 2-3 paragraphs and less than 300 words.
Capture the main points and be succinct. Reply only with the summary.
"""
task = "Most popular AI Agent frameworks in 2026"

settings = ModelSettings(tool_choice="required")
tools = [WebSearchTool()]


search_agent = Agent(
    name="Search Agent",
    tools=tools,
    instructions=INSTRUCTIONS,
    model_settings=settings,
    model=OPENAI_MODEL,
)
