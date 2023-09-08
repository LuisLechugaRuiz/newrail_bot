from newrail.agent.communication.broker.broker import Broker
from newrail.agent.config.config import AgentConfig


class RequestManager:
    def __init__(
        self,
        agent_config: AgentConfig,
        broker: Broker,
    ):
        self.agent_config = agent_config
        self.broker = broker

    def create_task(self, id: str, title: str, description: str, status: str) -> None:
        """Creates a task in the database."""

        self.broker.create_task(
            id=id,
            title=title,
            description=description,
            status=status,
        )

    def get_supervised_agents_info_str(self) -> str:
        """Returns a human readable string with the info of the supervised agents."""

        supervised_agents_info = self.broker.get_supervised_agents_info_str()
        return "\n".join(supervised_agents_info)

    def get_sibling_agents_info_str(self) -> str:
        """Returns a human readable string with the info of the sibling agents."""

        sibling_agents_info = self.broker.get_sibling_agents_info_str()
        return "\n".join(sibling_agents_info)

    def update_agent(self, agent_config: AgentConfig) -> None:
        """Updates the agent config."""

        self.agent_config = agent_config
        self.broker.update_agent(agent_config=agent_config)

    def update_task(self, task_id: str, status: str) -> None:
        """Updates the task status."""

        self.broker.update_task(task_id=task_id, status=status)

    def send_notification(self, event_type: str, **event_data):
        """Sends a notification to database."""

        self.broker.send_notification(event_type=event_type, **event_data)

    def send_message_to_agent(self, agent_name: str, message: str):
        """Verify that agent exists first and send message."""

        agent = self.broker.get_agent_info(agent_name=agent_name)
        if agent:
            self.broker.send_message(
                agent_id=agent["id"],
                team_id=agent["team_id"],
                organization_id=agent["organization_id"],
                message=message,
            )
            return f"Message sent to agent {agent_name}!"
        else:
            return f"Agent {agent_name} does not exist. Please check the name."

    # TODO: ADD send_message_to_user!
