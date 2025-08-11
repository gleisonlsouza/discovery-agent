from __future__ import annotations

from typing import List

from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai.agents.agent_builder.base_agent import BaseAgent

from .tools import ReadAnalysisJSONTool, GenerateGherkinStoriesTool


@CrewBase
class UserHistoriesCrew:
    """Crew that reads analysis.json and generates Gherkin user stories as .md files."""

    agents: List[BaseAgent]
    tasks: List[Task]

    @agent
    def analyst(self) -> Agent:
        return Agent(  # type: ignore
            config=self.agents_config["analyst"],  # type: ignore[index]
            tools=[ReadAnalysisJSONTool(), GenerateGherkinStoriesTool()],
            verbose=True,
        )

    @task
    def read_and_generate_task(self) -> Task:
        return Task(
            config=self.tasks_config["read_and_generate_task"],  # type: ignore[index]
        )

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )


