import asyncio
import logging
from collections.abc import AsyncIterator

from email_agent import email_agent
from planner_agent import WebSearchItem, planner_agent
from search_agent import search_agent
from writer_agent import ReportData, writer_agent

from agents import Runner, gen_trace_id, trace


class ResearchManager:
    async def run(self, query: str) -> AsyncIterator[str]:
        trace_id = gen_trace_id()

        with trace("Research Trace", trace_id=trace_id):
            yield (
                f"Starting research. Trace: "
                f"https://platform.openai.com/traces/trace?trace_id={trace_id}"
            )
            report = await self.write_report(query)
            yield report.report
            try:
                await self.send_email_with_report(query, report)
            except Exception:
                logging.exception("Failed to email the research report")
                yield report.report + "\n\n---\nEmail delivery failed. Your report is available above."

    # coroutine to search the web
    async def search(self, item: WebSearchItem) -> str:
        input_message = f"Search for {item.query}"
        result = await Runner.run(search_agent, input_message)

        return result.final_output

    # Coroutine to plan for the search

    async def search_plan(self, query: str) -> str:
        result = await Runner.run(planner_agent, f"Query: {query}")
        searches = result.final_output.searches
        tasks = [self.search(item) for item in searches]
        results = await asyncio.gather(*tasks)

        return results

    # Coroutine to write a report
    async def write_report(self, query: str) -> ReportData:
        search_results = await self.search_plan(query)
        result = await Runner.run(
            writer_agent, f"Original query: {query}\n Summarized search results: {search_results}"
        )

        return result.final_output

    # Coroutine to send email
    async def send_email_with_report(
        self, query: str, report_result: ReportData | None = None
    ) -> str:
        if report_result is None:
            report_result = await self.write_report(query)
        await Runner.run(email_agent, report_result.model_dump_json())

        return report_result.report
