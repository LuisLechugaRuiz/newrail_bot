import yaml
import os
import time
import uuid
from typing import List, Optional

from newrail.organization.organization import Organization
from newrail.organization.organization_config import OrganizationConfig
from newrail.config.config import Config
from newrail.agent.communication.database_handler.supabase_handler import (
    SupabaseHandler,
)
from newrail.capabilities.utils.builder import CapabilityBuilder

DEFAULT_CAPABILITIES = ["coordination", "edit_file"]


# Temporal file to upload info from a yaml to supabase.
class ConfigLoader:
    def __init__(
        self,
        architecture_filename: str = Config().architecture_filename,
    ):
        self.organization_id = Config().organization_id
        self.team_id = Config().team_id
        self.database_handler = SupabaseHandler()
        self.team_name = self.get_team_name()
        self.organization_name = self.get_organization_name()
        organization_config = OrganizationConfig(
            organization_name=self.organization_name,
            organization_id=self.organization_id,
            max_concurrent_agents=Config().max_concurrent_agents,
        )
        self.organization = Organization(organization_config=organization_config)
        self.architecture_path = os.path.join("architecture", architecture_filename)
        # Supabase loader
        self.load_to_database()

    def read_yaml_file(self, path: str):
        # Get the current script's directory
        script_dir = os.path.dirname(os.path.abspath(__file__))

        # Construct the absolute path to the YAML file
        abs_file_path = os.path.join(script_dir, path)

        with open(abs_file_path, "r") as file:
            data = yaml.safe_load(file)
        return data

    def get_capabilities(self):
        capabilities = self.database_handler.get_capabilities(
            organization_id=self.organization_id
        )
        capabilities_dict = {}
        for capability_data in capabilities.data:
            capabilities_dict[capability_data["name"]] = capability_data["id"]
        return capabilities_dict

    def get_organization_name(self) -> str:
        organization = self.database_handler.get_organization(
            organization_id=self.organization_id
        )
        return organization[0]["name"]

    def get_team_name(self) -> str:
        team = self.database_handler.get_team_from_id(
            organization_id=self.organization_id, team_id=self.team_id
        )
        return team[0]["name"]

    def load_to_database(self):
        self.database_handler.create_user(id=Config().user_id)
        self.database_handler.create_organization(id=self.organization_id)
        self.load_capabilities()
        self.load_teams(
            organization_name=Config().organization_name,
            organization_id=Config().organization_id,
        )
        self.load_iterations(num_iterations=100)

    def load_iterations(self, num_iterations: int):
        team = self.database_handler.get_team(
            organization_id=self.organization_id, team_name=self.team_name
        )
        self.database_handler.create_team_invocations(
            id=str(uuid.uuid4()),
            invoked_at=time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()),
            invoked_by_user_id=Config().user_id,
            team_id=team[0]["id"],
            team_name=self.team_name,
            num_iterations=num_iterations,
            organization_id=self.organization_id,
            organization_name=self.organization_name,
            status=0,
        )

    def load_teams(self, organization_name: str, organization_id: str):
        data = self.read_yaml_file(self.architecture_path)
        teams = []
        executive_director_agent_name = "executive_director"
        executive_director_agent_id = str(uuid.uuid4())
        root_team_id = str(uuid.uuid4())
        root_team_name = self.team_name
        self.database_handler.create_team(
            created_by_user_id=Config().user_id,
            id=root_team_id,
            name=root_team_name,
            mission="Global coordination and communication with users",
            organization_id=organization_id,
            organization_name=organization_name,
            lead_agent_id=executive_director_agent_id,
            lead_agent_name=executive_director_agent_name,
            status=0,
        )
        self.load_agent(
            created_by_user_id=Config().user_id,
            id=executive_director_agent_id,
            name=executive_director_agent_name,
            agent_mission="Coordinate your agents delegating tasks to them and monitoring their progress.",
            capabilities=["coordination"],
            organization_id=organization_id,
            team_name=root_team_name,
            team_id=root_team_id,
            is_lead=True,
        )
        for team in data["teams"]:
            team_id = str(uuid.uuid4())
            team_name = list(team.keys())[0]
            lead_agent_id = str(uuid.uuid4())
            lead_agent_name = team_name + "_leader"
            self.database_handler.create_team(
                created_by_user_id=Config().user_id,
                id=team_id,
                name=team_name,
                mission=team[team_name]["mission"],
                organization_id=organization_id,
                organization_name=organization_name,
                lead_agent_id=lead_agent_id,
                lead_agent_name=lead_agent_name,
                status=0,
            )
            # Create team leader
            team_mission = team[team_name]["mission"]
            team_leader_mission = f"Using effective task delegation and progress monitoring of your agents, ensure the accomplishment of the following mission: {team_mission}"
            self.load_agent(
                created_by_user_id=Config().user_id,
                id=lead_agent_id,
                name=lead_agent_name,
                agent_mission=team_leader_mission,
                capabilities=["coordination"],
                organization_id=organization_id,
                supervisor_id=executive_director_agent_id,
                supervisor_name=executive_director_agent_name,
                team_id=team_id,
                team_name=team_name,
                is_lead=True,
            )
            for agent_data in team[team_name]["agents"]:
                agent_name = list(agent_data.keys())[0]
                worker_capabilities = agent_data[agent_name]["capabilities"]
                for default_capability in DEFAULT_CAPABILITIES:
                    if default_capability not in worker_capabilities:
                        worker_capabilities.append(default_capability)
                self.load_agent(
                    created_by_user_id=Config().user_id,
                    id=str(uuid.uuid4()),
                    name=agent_name,
                    agent_mission=agent_data[agent_name]["mission"],
                    capabilities=worker_capabilities,
                    organization_id=organization_id,
                    supervisor_id=lead_agent_id,
                    supervisor_name=lead_agent_name,
                    team_id=team_id,
                    team_name=team_name,
                    is_lead=False,
                )
            teams.append((team_id, lead_agent_id))
        return teams

    def load_agent(
        self,
        created_by_user_id: str,
        id: str,
        name: str,
        agent_mission: str,
        capabilities: List[str],
        organization_id: str,
        team_id: str,
        team_name: str,
        is_lead: bool = False,
        supervisor_id: Optional[str] = None,
        supervisor_name: Optional[str] = None,
    ):
        self.database_handler.create_agent(
            created_by_user_id=created_by_user_id,
            id=id,
            name=name,
            mission=agent_mission,
            organization_id=organization_id,
            stage="PLAN_GOAL",
            status="WAITING",
            team_id=team_id,
            team_name=team_name,
            is_lead=is_lead,
            supervisor_id=supervisor_id,
            supervisor_name=supervisor_name,
        )
        capabilities_dict = self.get_capabilities()
        for capability in capabilities:
            self.database_handler.link_capability(
                agent_id=id,
                capability_id=capabilities_dict[capability],
                organization_id=organization_id,
            )

    def load_capabilities(self):
        capabilities = self._setup_capabilities()
        for capability in capabilities:
            self.database_handler.create_capability(
                id=str(uuid.uuid4()),
                name=capability,
                organization_id=Config().organization_id,
            )

    def _setup_capabilities(self):
        CapabilityBuilder.load_capabilities()
        capabilities = []
        for capability_name in CapabilityBuilder.CAPABILITIES.keys():
            capabilities.append(capability_name)
        return capabilities


def main():
    config_loader = ConfigLoader()


if __name__ == "__main__":
    main()
