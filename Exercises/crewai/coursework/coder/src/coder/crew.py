from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task  # pyright: ignore[reportMissingImports]

from .tools.sandbox_tools import sandbox_tools


@CrewBase
class Coder:
    """Coder crew"""

    agents: list[Agent]
    tasks: list[Task]

    @agent
    def coder(self) -> Agent:
        return Agent(config=self.agents_config["coder"], tools=sandbox_tools)

    @task
    def coding_task(self) -> Task:
        return Task(config=self.tasks_config["coding_task"])

    @crew
    def crew(self) -> Crew:
        """Creates the Coder crew"""

        return Crew(
            agents=self.agents,  # Automatically created by the @agent decorator
            tasks=self.tasks,  # Automatically created by the @task decorator
            process=Process.sequential,
            verbose=True,
        )
