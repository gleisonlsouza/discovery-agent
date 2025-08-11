from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai.agents.agent_builder.base_agent import BaseAgent
from typing import List

from .tools.repo_mcp_tools import (
    ListRepositoryFilesTool,
    ReadRepositoryFileTool,
)
from .tools.robust_search_repo_patterns import RobustSearchRepoPatternsTool
from .tools.chunk_tools import GetFileInfoTool, ReadFileChunkTool
from .tools.endpoint_scanner import EndpointScannerTool
from .tools.ui_router_scanner import UIRouterScannerTool
from .tools.visual_identity_scanner import VisualIdentityScannerTool
from .tools.validator_scanner import ValidatorScannerTool
from .tools.db_schema_scanner import DbSchemaScannerTool
from .tools.api_contract_scanner import ApiContractScannerTool
from .models import FinalAnalysisReport


@CrewBase
class DiscoveryAgent:
    """DiscoveryAgent crew specialized in repository reverse engineering and reporting."""

    agents: List[BaseAgent]
    tasks: List[Task]

    # Agents
    @agent
    def file_collector(self) -> Agent:
        return Agent(  # type: ignore
            config=self.agents_config["file_collector"],  # type: ignore[index]
            tools=[ListRepositoryFilesTool()],
            verbose=True,
        )

    @agent
    def architecture_analyst(self) -> Agent:
        return Agent(  # type: ignore
            config=self.agents_config["architecture_analyst"],  # type: ignore[index]
            tools=[ReadRepositoryFileTool(), RobustSearchRepoPatternsTool(), GetFileInfoTool(), ReadFileChunkTool(), DbSchemaScannerTool(), ApiContractScannerTool()],
            verbose=True,
        )

    @agent
    def entity_analyst(self) -> Agent:
        return Agent(  # type: ignore
            config=self.agents_config["entity_analyst"],  # type: ignore[index]
            tools=[ReadRepositoryFileTool(), RobustSearchRepoPatternsTool(), GetFileInfoTool(), ReadFileChunkTool(), DbSchemaScannerTool()],
            verbose=True,
        )

    @agent
    def business_rules_analyst(self) -> Agent:
        return Agent(  # type: ignore
            config=self.agents_config["business_rules_analyst"],  # type: ignore[index]
            tools=[ReadRepositoryFileTool(), RobustSearchRepoPatternsTool(), GetFileInfoTool(), ReadFileChunkTool(), ValidatorScannerTool()],
            verbose=True,
        )

    @agent
    def summarizer(self) -> Agent:
        return Agent(  # type: ignore
            config=self.agents_config["summarizer"],  # type: ignore[index]
            verbose=True,
        )

    @agent
    def modernization_consultant(self) -> Agent:
        return Agent(  # type: ignore
            config=self.agents_config["modernization_consultant"],  # type: ignore[index]
            verbose=True,
        )

    @agent
    def consolidator(self) -> Agent:
        return Agent(  # type: ignore
            config=self.agents_config["consolidator"],  # type: ignore[index]
            verbose=True,
        )

    @agent
    def project_classifier(self) -> Agent:
        return Agent(  # type: ignore
            config=self.agents_config["project_classifier"],  # type: ignore[index]
            verbose=True,
        )

    @agent
    def api_integrations_analyst(self) -> Agent:
        return Agent(  # type: ignore
            config=self.agents_config["api_integrations_analyst"],  # type: ignore[index]
            tools=[RobustSearchRepoPatternsTool(), ReadRepositoryFileTool(), GetFileInfoTool(), ReadFileChunkTool(), EndpointScannerTool(), ApiContractScannerTool()],
            verbose=True,
        )

    @agent
    def nfr_analyst(self) -> Agent:
        return Agent(  # type: ignore
            config=self.agents_config["nfr_analyst"],  # type: ignore[index]
            tools=[RobustSearchRepoPatternsTool(), ReadRepositoryFileTool(), GetFileInfoTool(), ReadFileChunkTool()],
            verbose=True,
        )

    @agent
    def security_analyst(self) -> Agent:
        return Agent(  # type: ignore
            config=self.agents_config["security_analyst"],  # type: ignore[index]
            tools=[RobustSearchRepoPatternsTool(), ReadRepositoryFileTool(), GetFileInfoTool(), ReadFileChunkTool()],
            verbose=True,
        )

    @agent
    def infra_analyst(self) -> Agent:
        return Agent(  # type: ignore
            config=self.agents_config["infra_analyst"],  # type: ignore[index]
            tools=[RobustSearchRepoPatternsTool(), ReadRepositoryFileTool(), GetFileInfoTool(), ReadFileChunkTool()],
            verbose=True,
        )

    @agent
    def ui_ux_analyst(self) -> Agent:
        return Agent(  # type: ignore
            config=self.agents_config["ui_ux_analyst"],  # type: ignore[index]
            tools=[RobustSearchRepoPatternsTool(), ReadRepositoryFileTool(), GetFileInfoTool(), ReadFileChunkTool(), UIRouterScannerTool(), VisualIdentityScannerTool()],
            verbose=True,
        )

    # Tasks
    @task
    def collect_files_task(self) -> Task:
        return Task(config=self.tasks_config["collect_files_task"])  # type: ignore[index]

    @task
    def analyze_architecture_task(self) -> Task:
        return Task(config=self.tasks_config["analyze_architecture_task"])  # type: ignore[index]

    @task
    def analyze_entities_task(self) -> Task:
        return Task(config=self.tasks_config["analyze_entities_task"])  # type: ignore[index]

    @task
    def analyze_business_rules_task(self) -> Task:
        return Task(config=self.tasks_config["analyze_business_rules_task"])  # type: ignore[index]

    @task
    def summarize_task(self) -> Task:
        return Task(config=self.tasks_config["summarize_task"])  # type: ignore[index]

    @task
    def modernization_task(self) -> Task:
        return Task(config=self.tasks_config["modernization_task"])  # type: ignore[index]

    @task
    def consolidate_task(self) -> Task:
        return Task(
            config=self.tasks_config["consolidate_task"],  # type: ignore[index]
            output_file="analysis.json",
            output_pydantic=FinalAnalysisReport,
        )

    @task
    def project_classification_task(self) -> Task:
        return Task(config=self.tasks_config["project_classification_task"])  # type: ignore[index]

    @task
    def api_integrations_task(self) -> Task:
        return Task(config=self.tasks_config["api_integrations_task"])  # type: ignore[index]

    @task
    def nfr_task(self) -> Task:
        return Task(config=self.tasks_config["nfr_task"])  # type: ignore[index]

    @task
    def security_task(self) -> Task:
        return Task(config=self.tasks_config["security_task"])  # type: ignore[index]

    @task
    def infra_task(self) -> Task:
        return Task(config=self.tasks_config["infra_task"])  # type: ignore[index]

    @task
    def ui_ux_task(self) -> Task:
        return Task(config=self.tasks_config["ui_ux_task"])  # type: ignore[index]

    # Crew
    @crew
    def crew(self) -> Crew:
        # Define explicit execution order so consolidation happens last
        ordered_tasks = [
            self.collect_files_task(),
            self.project_classification_task(),
            self.analyze_architecture_task(),
            self.analyze_entities_task(),
            self.analyze_business_rules_task(),
            self.api_integrations_task(),
            self.nfr_task(),
            self.security_task(),
            self.infra_task(),
            self.ui_ux_task(),
            self.summarize_task(),
            self.modernization_task(),
            self.consolidate_task(),
        ]

        return Crew(
            agents=self.agents,
            tasks=ordered_tasks,
            process=Process.sequential,
            verbose=True,
        )
