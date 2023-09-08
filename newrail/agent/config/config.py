import json
import os
import shutil
from threading import RLock
from typing import List, Optional

from newrail.agent.config.stage import Stage
from newrail.agent.config.status import Status
from newrail.utils.storage import get_org_folder


class AgentConfig(object):
    def __init__(
        self,
        created_by_user_id: str,
        id: str,
        name: str,
        organization_id: str,
        organization_name: str,
        mission: str,
        capabilities: List[str],
        team_id: str,
        team_name: str,
        is_lead: bool,
        supervisor_id: Optional[str],
        supervisor_name: Optional[str],
        stage: Stage = Stage.PLANNING,
        status: Status = Status.WAITING,
    ):
        self.created_by_user_id = created_by_user_id
        self.id = id
        self.name = name
        self.organization_id = organization_id
        self.organization_name = organization_name
        self.mission = mission
        self.capabilities = capabilities
        self.supervisor_id = supervisor_id
        self.supervisor_name = supervisor_name
        self.team_id = team_id
        self.team_name = team_name
        self.is_lead = is_lead
        self.stage = stage
        self.status = status
        self._stage_lock = RLock()
        self._status_lock = RLock()
        self.save()

    def get_stage(self) -> Stage:
        with self._stage_lock:
            return self.stage

    def set_stage(self, stage: Stage) -> None:
        with self._stage_lock:
            self.stage = stage
            self.save()

    def get_status(self) -> Status:
        with self._status_lock:
            return self.status

    def set_status(self, status: Status) -> None:
        with self._status_lock:
            self.status = status
            self.save()

    @classmethod
    def get_config_file_path(cls, agent_folder: str) -> str:
        return os.path.join(agent_folder, "config.yaml")

    @classmethod
    def get_folder(cls, organization_name: str, name: str) -> str:
        return os.path.join(get_org_folder(organization_name), "agents", name)

    @property
    def folder(self) -> str:
        return self.get_folder(self.organization_name, self.name)

    @classmethod
    def load(cls, folder: str) -> Optional["AgentConfig"]:
        try:
            config_file_path = cls.get_config_file_path(folder)
            with open(config_file_path) as f:
                data = json.load(f)
                return cls.from_json(data)
        except FileNotFoundError:
            return None

    def save(self) -> None:
        config_file = self.get_config_file_path(self.folder)
        os.makedirs(os.path.dirname(config_file), exist_ok=True)
        with open(config_file, "w") as f:
            f.write(json.dumps(self.to_dict(), indent=2))

    def remove(self) -> bool:
        if os.path.isdir(self.folder):
            shutil.rmtree(self.folder)
            return True
        else:
            return False

    def to_dict(self):
        return {
            "created_by_user_id": self.created_by_user_id,
            "id": self.id,
            "is_lead": self.is_lead,
            "name": self.name,
            "mission": self.mission,
            "organization_id": self.organization_id,
            "supervisor_id": self.supervisor_id,
            "supervisor_name": self.supervisor_name,
            "team_id": self.team_id,
            "team_name": self.team_name,
            "stage": self.stage.name,
            "status": self.status.name,
        }

    @classmethod
    def from_json(cls, data) -> "AgentConfig":
        return AgentConfig(
            created_by_user_id=data["created_by_user_id"],
            id=data["id"],
            name=data["name"],
            is_lead=data["is_lead"],
            organization_id=data["organization_id"],
            organization_name=data["organization_name"],
            mission=data["mission"],
            capabilities=data["capabilities"],
            supervisor_id=data["supervisor_id"],
            supervisor_name=data["supervisor_name"],
            team_id=data["team_id"],
            team_name=data["team_name"],
            stage=Stage[data["stage"]],
            status=Status[data["status"]],
        )
