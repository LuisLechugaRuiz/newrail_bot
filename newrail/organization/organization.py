from typing import Dict, List, Optional
from threading import RLock


from newrail.agent.agent import Agent
from newrail.agent.config.config import AgentConfig
from newrail.agent.config.stage import Stage
from newrail.agent.config.status import Status
from newrail.capabilities.utils.builder import CapabilityBuilder
from newrail.memory.long_term_memory.weaviate import WeaviateMemory
from newrail.organization.utils.logger.org_logger import OrgLogger
from newrail.organization.organization_config import OrganizationConfig
from newrail.organization.team.team import Team
from newrail.organization.team.team_config import TeamConfig
from newrail.organization.utils.orchestrator import Orchestrator
from newrail.utils.storage import get_org_folder


class Organization:
    def __init__(self, organization_config: OrganizationConfig):
        self.organization_config = organization_config
        self.organization_logger = OrgLogger(
            organization_name="organization",
            organization_folder=self.organization_config.folder,
            process_name="main",
        )
        self._agents: Dict[str, Agent] = {}
        self._agents_lock = RLock()
        self._teams: Dict[str, Team] = {}
        self._teams_lock = RLock()
        self.long_term_memory = (
            WeaviateMemory()
        )  # Access to long term memory to manage org operations
        self.orchestator = Orchestrator(
            logger=self.organization_logger,
            max_concurrent_agents=organization_config.max_concurrent_agents,
        )
        self._orchestator_lock = RLock()

        # Load capabilities.
        CapabilityBuilder.load_capabilities()

    def add_agent(self, agent: Agent) -> None:
        """Thread safe method to add an agent. Only entry point."""

        with self._agents_lock:
            self._agents[agent.cfg.name] = agent
        self.add_agent_to_team(agent_name=agent.cfg.name, team_name=agent.cfg.team_name)
        with self._orchestator_lock:
            self.orchestator.add_agent(agent)
            agent.update_status(status=agent.cfg.status)
            self.orchestator.insert_agent(agent_name=agent.cfg.name)

    def add_agent_to_team(self, agent_name: str, team_name: str) -> None:
        """Thread safe method to add an agent to a team. Only entry point."""

        with self._teams_lock:
            team = self._teams.get(team_name)
            if team:
                if agent_name != team.cfg.lead_agent_name:
                    team.add_member(agent_name)
            else:
                self.organization_logger.log(
                    f"Can't find team {team_name} to add agent {agent_name}"
                )

    def add_team(self, team: Team) -> None:
        """Thread safe method to add a team. Only entry point."""

        with self._teams_lock:
            self._teams[team.cfg.name] = team

    def add_existing_agent(self, agent_config: AgentConfig) -> Agent:
        """Method to add an existing agent to the organization."""

        self.organization_logger.log(
            f"Adding existing agent with name {agent_config.name}"
        )
        agent = Agent(
            agent_config=agent_config,
        )
        self.add_agent(agent)
        return agent

    def add_existing_team(self, team_config: TeamConfig) -> Team:
        """Method to add an existing team to the organization."""

        self.organization_logger.log(
            f"Adding existing team with name {team_config.name}"
        )
        team = Team(
            organization_name=self.organization_config.organization_name,
            organization_folder=self.organization_config.folder,
            team_config=team_config,
        )
        self.add_team(team)
        return team

    def create_agent(
        self,
        created_by_user_id: str,
        id: str,
        name: str,
        is_lead: bool,
        organization_id: str,
        organization_name: str,
        mission: str,
        capabilities: List[str],
        team_id: str,
        team_name: str,
        stage: str,
        status: str,
        supervisor_id: Optional[str] = None,
        supervisor_name: Optional[str] = None,
    ) -> Agent:
        """Method to create agent an agent from scratch."""

        self.long_term_memory.create_agent(agent_name=name, agent_id=id)
        agent_config = AgentConfig(
            created_by_user_id=created_by_user_id,
            id=id,
            name=name,
            is_lead=is_lead,
            organization_id=organization_id,
            organization_name=organization_name,
            mission=mission,
            capabilities=capabilities,
            team_id=team_id,
            team_name=team_name,
            supervisor_name=supervisor_name,
            supervisor_id=supervisor_id,
            stage=Stage[stage],
            status=Status[status],
        )
        new_agent = Agent(
            agent_config=agent_config,
        )
        self.organization_logger.log(
            f"New agent created with name: {new_agent.cfg.name}",
            should_print=True,
        )
        self.add_agent(new_agent)

        return new_agent

    def create_team(
        self,
        created_by_user_id: str,
        name: str,
        id: str,
        organization_id: str,
        organization_name: str,
        mission: str,
        lead_agent_id: str,
        lead_agent_name: str,
        supervisor_id: str,
        supervisor_name: str,
    ) -> Team:
        self.long_term_memory.create_team(team_name=name, team_id=id)
        team_config = TeamConfig(
            created_by_user_id=created_by_user_id,
            name=name,
            id=id,
            organization_id=organization_id,
            organization_name=organization_name,
            mission=mission,
            lead_agent_id=lead_agent_id,
            lead_agent_name=lead_agent_name,
            supervisor_id=supervisor_id,
            supervisor_name=supervisor_name,
        )
        new_team = Team(
            organization_name=self.organization_config.organization_name,
            organization_folder=self.organization_config.folder,
            team_config=team_config,
        )
        self.add_team(new_team)
        return new_team

    def update_protagonist(self, agent_name: str) -> None:
        self.organization_logger.update_protagonist(protagonist_name=agent_name)

    def delete_agent(self, agent_name: str) -> bool:
        """Thread safe delete agent."""

        with self._agents_lock:
            agents = self._agents
            agent = agents.get(agent_name)
            if agent:
                agent.delete()
                del agents[agent_name]
                return True
            return False

    def is_running(self) -> bool:
        return self.orchestator.is_running()

    def run(self, max_iterations: int) -> None:
        with self._orchestator_lock:
            self.orchestator.start(max_iterations=max_iterations)
