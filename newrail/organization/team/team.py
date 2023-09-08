from typing import List

from newrail.config.config import Config
from newrail.memory.long_term_memory.weaviate import WeaviateMemory
from newrail.organization.team.team_config import TeamConfig
from newrail.organization.utils.logger.org_logger import OrgLogger


class Team:
    def __init__(
        self,
        organization_name: str,
        organization_folder: str,
        team_config: TeamConfig,
    ):
        self.organization_name = organization_name
        self.organization_folder = organization_folder
        self.cfg = team_config
        self.global_cfg = Config()
        self.logger = OrgLogger(
            organization_name=self.cfg.organization_name,
            organization_folder=self.cfg.get_folder(
                organization_name=organization_name, name=self.cfg.name
            ),
            process_name="main",
        )
        self.long_term_memory = WeaviateMemory()

    def add_member(self, agent_name: str) -> None:
        self.cfg.add_member(agent_name)

    def get_team_members(self) -> List[str]:
        return self.cfg.get_members()

    # TODO: Implement as needed to ensure clean-up after agent is deleted.
    def delete(self):
        """Called by org if the agent should be deleted."""

        self.cfg.remove()
        return True
