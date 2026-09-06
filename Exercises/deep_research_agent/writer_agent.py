import os

from dotenv import load_dotenv
from pydantic import BaseModel, Field

from agents import Agent

load_dotenv()
OPENAI_MODEL = os.getenv("DEFAULT_MODEL", "gpt-5.4-nano")


INSTRUCTIONS = """
You are a senior researcher tasked with writing a cohesive report for a research query.
You will be provided with the original query, and some research.
Generate a comprehensive report based on the research and the query.
The final output should be in markdown format, and it should be lengthy and detailed. Aim 
for 5-10 pages of content, at least 1000 words.
"""


class ReportData(BaseModel):
    short_summary: str = Field(description="A Short cummary of the research content")
    report: str = Field(description="The research report in Markdown format")
    follow_up_questions: str = Field(description="Follow-up questions on the research tiem")


writer_agent = Agent(
    name="Writer Agent", model=OPENAI_MODEL, instructions=INSTRUCTIONS, output_type=ReportData
)
