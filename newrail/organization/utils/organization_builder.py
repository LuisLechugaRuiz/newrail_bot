from colorama import Fore
import glob
import os
from pathlib import Path
import shutil
from typing import List

from newrail.agent.agent import Agent
from newrail.agent.config.config import AgentConfig
from newrail.organization.team.team_config import TeamConfig
from newrail.organization.utils.logger.org_logger import OrgLogger
from newrail.organization.organization import Organization
from newrail.organization.organization_config import OrganizationConfig
from newrail.config.config import Config
from newrail.utils.print_utils import (
    print_to_console,
)


class OrganizationBuilder(object):
    @classmethod
    def get_org_folder(cls, organization_name: str):
        organization_name = (
            organization_name.lower().replace(" ", "_")
            if organization_name and " " in organization_name
            else organization_name
        )
        return os.path.join(Config().organizations_folder, organization_name)

    @classmethod
    def load(cls, organization_name: str):
        organization_folder = cls.get_org_folder(organization_name)
        logger = OrgLogger(
            organization_name=organization_name,
            organization_folder=os.path.join(organization_folder, "organization"),
            process_name="setup",
        )
        # Verify that director exists.
        director_folder = AgentConfig.get_folder(
            organization_name, "executive_director"
        )
        director_folder_path = Path(director_folder)
        if director_folder_path.exists() and director_folder_path.is_dir():
            organization_config = OrganizationConfig.load(organization_folder)
            if not organization_config:
                logger.log(
                    message=f"Organization config not found in: {organization_folder}",
                    should_print=True,
                )
                return None
            logger.log(
                message=f"Loading existing organization config from: {organization_folder}",
                should_print=True,
            )
            org = Organization(
                organization_config=organization_config,
            )
            # Load director agent config
            director_config = AgentConfig.load(director_folder)
            if director_config:
                teams_folder = glob.glob(os.path.join(organization_folder, "teams/*"))
                for team_folder in teams_folder:
                    team_config = TeamConfig.load(team_folder)
                    if team_config is not None:
                        org.add_existing_team(team_config=team_config)
                agents: List[Agent] = []
                # Load all agent configs and add to organization
                agents_folder = glob.glob(os.path.join(organization_folder, "agents/*"))
                for agent_folder in agents_folder:
                    agent_config = AgentConfig.load(agent_folder)
                    if agent_config is not None:
                        agents.append(org.add_existing_agent(agent_config=agent_config))
                return org
            logger.log("Director config not found, can't load organization")
            return None
        # director doesn't exist, remove organization folder as this should be a left over.
        try:
            shutil.rmtree(organization_folder)
            print(f"Remove wrong organization: {organization_folder}")
        except OSError as e:
            print(f"Organization {organization_folder} doesn't exists, error: {e}")
        return None

    @classmethod
    def create_organization_config(
        cls, organization_name, organization_id, max_concurrent_agents
    ):
        """Create a new configuration for an organization, use carefully."""

        organization_config = OrganizationConfig(
            organization_name=organization_name,
            organization_id=organization_id,
            max_concurrent_agents=max_concurrent_agents,
        )
        return organization_config

    @classmethod
    def create_new_org(
        cls,
        organization_name: str,
        organization_id: str,
        max_concurrent_agents=Config().max_concurrent_agents,
    ):
        organization_config = cls.create_organization_config(
            organization_name=organization_name,
            organization_id=organization_id,
            max_concurrent_agents=max_concurrent_agents,
        )
        new_organization = Organization(
            organization_config=organization_config,
        )
        org_folder = organization_config.folder
        Path(org_folder).mkdir(parents=True, exist_ok=True)
        data_folder = os.path.join(org_folder, "data")
        Path(data_folder).mkdir(parents=True, exist_ok=True)
        return new_organization

    @classmethod
    def get_organization(cls, should_speak=False):
        while True:
            if not os.path.exists(Config().organizations_folder):
                os.makedirs(Config().organizations_folder, exist_ok=True)
            organizations = os.listdir(Config().organizations_folder)
            if organizations:
                organizations_intro = []
                organizations_intro = {}
                for index, organization in enumerate(organizations):
                    organizations_intro[index] = organization
                print_to_console(
                    "Welcome back! ",
                    Fore.GREEN,
                    "these are the existing organizations:",
                    speak_text=should_speak,
                )
                for index, organization in organizations_intro.items():
                    print_to_console(
                        f"{index} - ",
                        Fore.GREEN,
                        f"{organization}",
                        speak_text=should_speak,
                    )
                should_continue = input(
                    "Do you want to continue running any of the existing ones? (y/n): "
                )
                if should_continue.lower() == "y":
                    number = int(
                        input(
                            "Please specify the number of the existing organization: "
                        )
                    )
                    if number in organizations_intro:
                        organization = OrganizationBuilder.load(
                            organizations_intro[number]
                        )
                        if organization:
                            return organization
                        print("Organization was malformed, removing org.")
                    else:
                        print(
                            f"Organization with id: {number} doesn't exist, try again."
                        )
                else:
                    break
            else:
                break
        return OrganizationBuilder.create_new_org()
