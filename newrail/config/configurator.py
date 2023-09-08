import os
import uuid
import shutil
from typing import Optional

from newrail.agent.config.stage import Stage
from newrail.agent.config.status import Status
from newrail.agent.communication.database_handler.supabase_handler import (
    SupabaseHandler,
)
from newrail.config.config import Config
from newrail.capabilities.utils.builder import CapabilityBuilder

from newrail.memory.utils.task.task import Task
from newrail.memory.utils.task.task_status import TaskStatus
from newrail.organization.utils.logger.logger import Logger
from newrail.organization.organization import Organization
from newrail.organization.utils.organization_builder import OrganizationBuilder


DEFAULT_CAPABILITIES = ["coordination"]


class Configurator:
    def __init__(
        self,
    ):
        self.organization_id = Config().organization_id
        self.team_id = Config().team_id
        self.database_handler = SupabaseHandler()
        self.organization_name = self.get_organization_name()
        self.team_name = self.get_team_name()
        Logger(protagonist=self.get_lead_agent_name())
        self.organization = OrganizationBuilder.create_new_org(
            organization_id=self.organization_id,
            organization_name=self.organization_name,
        )
        # TODO: Improve this, don't save config on start
        Config().organization_data = os.path.join(
            OrganizationBuilder().get_org_folder(
                organization_name=self.organization_name
            ),
            "data",
        )
        self.add_files()
        self.load_to_database()

    def add_files(self) -> None:
        files_path = os.path.join(Config().permanent_storage, "files")
        shutil.copytree(files_path, Config().organization_data, dirs_exist_ok=True)

    def create_agent_tree(self, lead_agent_name: str):
        supervised_agents = self.database_handler.get_supervised_agent(
            organization_id=self.organization_id,
            supervisor_name=lead_agent_name,
        )
        for agent in supervised_agents:
            if agent["is_lead"]:
                self.create_team(team_name=agent["team_name"])
                self.create_agent(
                    agent_name=agent["name"], team_name=agent["team_name"]
                )
                # Create agents recursively
                self.create_agent_tree(lead_agent_name=agent["name"])
            else:
                self.create_agent(
                    agent_name=agent["name"], team_name=agent["team_name"]
                )

    def create_agent(self, agent_name: str, team_name: str):
        agent_capabilities = self.database_handler.get_agent_capabilities(
            organization_id=self.organization_id,
            agent_name=agent_name,
            team_name=team_name,
        )
        if len(agent_capabilities) > 1:
            print("Agent capabilities:", agent_capabilities)
            raise Exception(f"More than one agent with the same name: {agent_name}")
        agent_capabilities = agent_capabilities[0]
        capabilities = [
            capability["name"] for capability in agent_capabilities["capabilities"]
        ]
        for default_capability in DEFAULT_CAPABILITIES:
            if default_capability not in capabilities:
                capabilities.append(default_capability)
        status = agent_capabilities["status"]
        if not status:
            status = Status.WAITING.name
        stage = agent_capabilities["stage"]
        if not stage:
            stage = Stage.PLANNING.name

        agent = self.organization.create_agent(
            created_by_user_id=agent_capabilities["created_by_user_id"],
            id=agent_capabilities["id"],
            name=agent_capabilities["name"],
            is_lead=agent_capabilities["is_lead"],
            organization_name=self.organization_name,
            organization_id=self.organization_id,
            mission=agent_capabilities["mission"],
            capabilities=capabilities,
            team_id=agent_capabilities["team_id"],
            team_name=team_name,
            supervisor_id=agent_capabilities["supervisor_id"],
            supervisor_name=agent_capabilities["supervisor_name"],
            status=status,
            stage=stage,
        )
        tasks = self.database_handler.get_tasks(
            organization_id=self.organization_id, agent_id=agent_capabilities["id"]
        )
        if tasks:
            agent.update_status(status=agent.cfg.status)
        for task in tasks:
            description = task["description"]
            if not description:
                description = ""
            status = task["status"]
            if status != TaskStatus.DONE.value:
                agent.add_task(
                    Task(
                        id=task["id"],
                        title=task["title"],
                        description=description,
                        status=status,
                    )
                )

    def create_team(self, team_name: str):
        team = self.database_handler.get_team(
            organization_id=self.organization_id, team_name=team_name
        )
        if len(team) > 1:
            raise Exception("Multiple teams with the same name.")
        team = team[0]
        new_team = self.organization.create_team(
            created_by_user_id=team["created_by_user_id"],
            name=team["name"],
            id=team["id"],
            organization_id=team["organization_id"],
            organization_name=team["organization_name"],
            mission=team["mission"],
            supervisor_id=team["supervisor_id"],
            supervisor_name=team["supervisor_name"],
            lead_agent_id=team["lead_agent_id"],
            lead_agent_name=team["lead_agent_name"],
        )
        return new_team

    def delete_team_invocations(self, team_invocations_id: str):
        self.database_handler.delete_team_invocations(
            team_invocations_id=team_invocations_id
        )

    def get_capabilities(self):
        capabilities = self.database_handler.get_capabilities(
            organization_id=self.organization_id
        )
        capabilities_dict = {}
        for capability_data in capabilities.data:
            capabilities_dict[capability_data["name"]] = capability_data["id"]
        return capabilities_dict

    def get_team_invocations(self):
        team_invocations = self.database_handler.get_team_invocations(
            organization_id=self.organization_id, team_name=self.team_name
        )
        if len(team_invocations) > 0:
            return team_invocations[0]
        return None

    def get_lead_agent_name(self) -> str:
        team = self.database_handler.get_team(
            organization_id=self.organization_id, team_name=self.team_name
        )
        return team[0]["lead_agent_name"]

    def get_team_name(self) -> str:
        team = self.database_handler.get_team_from_id(
            organization_id=self.organization_id, team_id=self.team_id
        )
        return team[0]["name"]

    def get_organization_name(self) -> str:
        organization = self.database_handler.get_organization(
            organization_id=self.organization_id
        )
        return organization[0]["name"]

    def load_to_database(self):
        self.load_capabilities()

    def load_capabilities(self):
        capabilities = self._setup_capabilities()
        for capability in capabilities:
            self.database_handler.create_capability(
                id=str(uuid.uuid4()),
                name=capability,
                organization_id=Config().organization_id,
            )

    def update_team_invocations(self, team_invocations_id: str, status: str):
        self.database_handler.update_team_invocations(
            team_invocations_id=team_invocations_id, status=status
        )

    def setup(self) -> Optional[Organization]:
        try:
            # 1. Create root team.
            root_team = self.create_team(team_name=self.team_name)
            # 2. Create root agent.
            lead_agent_name = root_team.cfg.lead_agent_name
            self.create_agent(agent_name=lead_agent_name, team_name=self.team_name)
            # 3. Create the rest of the agents recursively.
            self.create_agent_tree(lead_agent_name=lead_agent_name)
            return self.organization
        except Exception as e:
            print("Error setting up the organization, error:", e)
            return None

    def _setup_capabilities(self):
        CapabilityBuilder.load_capabilities()
        capabilities = []
        for capability_name in CapabilityBuilder.CAPABILITIES.keys():
            capabilities.append(capability_name)
        return capabilities


def main():
    configurator = Configurator()
    configurator.setup()


if __name__ == "__main__":
    main()
