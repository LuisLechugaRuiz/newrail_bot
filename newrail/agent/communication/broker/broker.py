from datetime import datetime
from realtime.types import Callback
import uuid

from newrail.agent.config.config import AgentConfig
from newrail.agent.communication.database_handler.supabase_handler import (
    SupabaseHandler,
)
from newrail.config.config import Config
from newrail.organization.utils.logger.agent_logger import AgentLogger


class Broker:
    def __init__(self, agent_config: AgentConfig, agent_logger: AgentLogger):
        self.organization_id = Config().organization_id
        self.agent_config = agent_config
        self.database_handler = SupabaseHandler()
        self.agent_logger = agent_logger.create_logger("broker")

    def create_task(self, id: str, title: str, description: str, status: str):
        self.database_handler.create_task(
            id=id,
            organization_id=self.organization_id,
            agent_id=self.agent_config.id,
            title=title,
            description=description,
            status=status,
        )

    def get_agent_info(self, agent_name: str):
        """Get agent info"""

        agent = self.database_handler.get_agent(
            organization_id=self.organization_id,
            agent_name=agent_name,
        )
        if len(agent) > 1:
            self.agent_logger.log_critical("Agent exists twice in database!!")

        return agent[0]

    def get_agent_info_from_id(self, agent_id: str):
        agent = self.database_handler.get_agent_from_id(
            organization_id=self.organization_id,
            agent_id=agent_id,
        )
        if len(agent) > 1:
            self.agent_logger.log_critical("Agent exists twice in database!!")

        return agent[0]

    def get_user_info_from_id(self, user_id: str):
        user = self.database_handler.get_user_from_id(
            user_id=user_id,
        )
        if len(user) > 1:
            self.agent_logger.log_critical("User exists twice in database!!")

        return user[0]

    def get_supervised_agents_info_str(self):
        supervised_agents = self.database_handler.get_supervised_agent(
            organization_id=self.organization_id,
            supervisor_name=self.agent_config.name,
        )
        return [
            self._get_agent_info(supervised_agent)
            for supervised_agent in supervised_agents
        ]

    def get_sibling_agents_info_str(self):
        supervisor_name = self.agent_config.supervisor_name
        if supervisor_name:
            sibling_agents = self.database_handler.get_supervised_agent(
                organization_id=self.organization_id,
                supervisor_name=self.agent_config.supervisor_name,
            )
            siblings_info = []
            for sibling_agent in sibling_agents:
                if sibling_agent["name"] != self.agent_config.name:
                    siblings_info.append(sibling_agent)
            return siblings_info
        else:
            return []

    def _get_agent_info(self, agent_data):
        agent_name = agent_data["name"]
        agent_mission = agent_data["mission"]
        return f"Agent name: {agent_name}, mission: {agent_mission}"

    def update_agent(self, agent_config: AgentConfig):
        self.agent_config = agent_config
        agent_data = agent_config.to_dict()
        self.database_handler.update_agent(**agent_data)

    def update_task(self, task_id: str, status: str):
        """Update task status in database"""

        self.database_handler.update_task(task_id=task_id, status=status)

    def send_message(
        self, agent_id: str, team_id: str, organization_id: str, message: str
    ):
        message_data = {
            "agent_id": self.agent_config.id,
            "message": message,
        }
        data = {
            "agent_id": agent_id,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "data": message_data,
            "request_type": "message_from_agent",
            "organization_id": organization_id,
            "team_id": team_id,
        }
        self.database_handler.send_event(**data)

    def send_notification(
        self,
        event_type: str,
        **event_data,
    ):
        data = {
            "agent_id": self.agent_config.id,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "data": event_data,
            "event_type": event_type,
            "id": str(uuid.uuid4()),
            "organization_id": self.agent_config.organization_id,
            "team_id": self.agent_config.team_id,
        }
        self.database_handler.send_notification(**data)

    def subscribe_to_channel(
        self, schema: str, table_name: str, event_type: str, callback: Callback
    ):
        self.database_handler.subscribe_to_channel(
            schema=schema,
            table_name=table_name,
            event_type=event_type,
            callback=callback,
        )

    def start_realtime_listener(self):
        self.database_handler.start_realtime_listener()
