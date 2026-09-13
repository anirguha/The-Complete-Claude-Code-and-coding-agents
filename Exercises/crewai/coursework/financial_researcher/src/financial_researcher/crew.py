from typing import Any, cast

from crewai import Agent, Crew, Process, Task

try:
    from crewai.project import CrewBase, agent, crew, task  # type: ignore[import-not-found]
except ImportError:
    CrewBase = cast(Any, lambda cls: cls)
    agent = cast(Any, lambda func: property(func))
    crew = cast(Any, lambda func: property(func))
    task = cast(Any, lambda func: property(func))
try:
    from crewai_tools import SerperDevTool  # type: ignore[import-not-found]
except ImportError:
    SerperDevTool = None


@CrewBase
class FinancialResearcher:
    """FinancialResearcher crew"""

    agents: list[Agent]
    tasks: list[Task]

    @agent
    def researcher(self) -> Agent:
        tools = [SerperDevTool()] if SerperDevTool else []
        return Agent(config=self.agents_config["researcher"], verbose=True, tools=tools)

    @agent
    def analyst(self) -> Agent:
        return Agent(config=self.agents_config["analyst"], verbose=True)

    @task
    def research_task(self) -> Task:
        return Task(config=self.tasks_config["research_task"])

    @task
    def analysis_task(self) -> Task:
        return Task(config=self.tasks_config["analysis_task"], output_file="output/report.md")

    @crew
    def crew(self) -> Crew:
        """Creates the FinancialResearcher crew"""
        # To learn how to add knowledge sources to your crew, check out the documentation:
        # https://docs.crewai.com/concepts/knowledge#what-is-knowledge

        return Crew(
            agents=self.agents,  # Automatically created by the @agent decorator
            tasks=self.tasks,  # Automatically created by the @task decorator
            process=Process.sequential,
            verbose=True,
            tracing=True,
            # process=Process.hierarchical, # In case you wanna use that instead https://docs.crewai.com/how-to/Hierarchical/
        )
