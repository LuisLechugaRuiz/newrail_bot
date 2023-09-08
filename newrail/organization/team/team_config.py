import json
import os
import shutil
from threading import RLock
from typing import Optional, List

from newrail.utils.storage import get_org_folder


class TeamConfig(object):
    def __init__(
        self,
        created_by_user_id: str,
        id: str,
        name: str,
        organization_id: str,
        organization_name: str,
        mission: str,
        lead_agent_id: str,
        lead_agent_name: str,
        supervisor_id: str,
        supervisor_name: str,
    ):
        self.created_by_user_id = created_by_user_id
        self.id = id
        self.name = name
        self.organization_id = organization_id
        self.organization_name = organization_name
        self.mission = mission
        self.lead_agent_id = lead_agent_id
        self.lead_agent_name = lead_agent_name
        self.supervisor_id = supervisor_id
        self.supervisor_name = supervisor_name
        self.names = []
        self.save()

    def add_member(self, agent_name: str) -> None:
        self.names.append(agent_name)
        self.save()

    def get_members(self) -> List[str]:
        return self.names

    @classmethod
    def get_config_file_path(cls, agent_folder: str) -> str:
        return os.path.join(agent_folder, "config.yaml")

    @classmethod
    def get_folder(cls, organization_name: str, name: str) -> str:
        return os.path.join(get_org_folder(organization_name), "teams", name)

    @property
    def folder(self) -> str:
        return self.get_folder(self.organization_name, self.name)

    @classmethod
    def load(cls, folder: str) -> Optional["TeamConfig"]:
        try:
            config_file_path = cls.get_config_file_path(folder)
            with open(config_file_path) as f:
                data = json.load(f)
                return cls.from_json(data)
        except FileNotFoundError:
            return None

    def remove(self) -> bool:
        if os.path.isdir(self.folder):
            shutil.rmtree(self.folder)
            return True
        else:
            return False

    def save(self) -> None:
        config_file = self.get_config_file_path(self.folder)
        os.makedirs(os.path.dirname(config_file), exist_ok=True)
        with open(config_file, "w") as f:
            f.write(json.dumps(self.to_dict(), indent=2))

    def to_dict(self):
        return {
            "created_by_user_id": self.created_by_user_id,
            "name": self.name,
            "id": self.id,
            "organization_id": self.organization_id,
            "organization_name": self.organization_name,
            "mission": self.mission,
            "lead_agent_id": self.lead_agent_id,
            "lead_agent_name": self.lead_agent_name,
            "supervisor_id": self.supervisor_id,
            "supervisor_name": self.supervisor_name,
        }

    @classmethod
    def from_json(cls, data) -> "TeamConfig":
        return TeamConfig(
            created_by_user_id=data["created_by_user_id"],
            id=data["id"],
            name=data["name"],
            organization_id=data["organization_id"],
            organization_name=data["organization_name"],
            mission=data["mission"],
            lead_agent_id=data["lead_agent_id"],
            lead_agent_name=data["lead_agent_name"],
            supervisor_id=data["supervisor_id"],
            supervisor_name=data["supervisor_name"],
        )
