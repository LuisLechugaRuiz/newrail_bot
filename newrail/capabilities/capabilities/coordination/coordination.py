from newrail.capabilities.capability import Capability
from newrail.capabilities.utils.decorators import (
    action_decorator,
    context_decorator,
)


class Coordination(Capability):
    """
    Enables to communicate with other agents and wait for specific events (e.g other agent to achieve a goal).
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @context_decorator
    def get_agents(self) -> str:
        """

        Returns:
            str: Get agents for communication.
        """

        agent_info = f"You are: {self.agent_config.name}. You supervisor is: {self.agent_config.supervisor_name}\n"
        supervised_agents = self.request_manager.get_supervised_agents_info_str()
        if supervised_agents:
            agent_info += f"\nAgents under your supervision:\n{supervised_agents}"
        sibling_agents = self.request_manager.get_sibling_agents_info_str()
        if sibling_agents:
            agent_info += f"\nAgents which coolaborate with you:\n{sibling_agents}"
        return agent_info

    @action_decorator
    def talk_to_agent(self, agent_name: str, message: str) -> str:
        """Talk to another agent. Use this action to talk with a single agent.
        In case you want to talk to multiple agents, please call this action multiple times.

        Args:
            agent_name (str): The name of the agent to talk to
            message (str): The message
        Returns:
            str: Result of the operation
        """

        return str(
            self.request_manager.send_message_to_agent(
                agent_name=agent_name, message=message
            )
        )

    @action_decorator
    def wait(self, event: str) -> str:
        """Pause the current activity and wait for a specific event or condition. Useful after assigning a goal to an agent to wait until the a report is received.

        Args:
            event (str): The explanation of the specific event or condition for which the agent is waiting. E.g: "The result of the search from agent X"
        Returns:
            str: Result of the waiting operation.
        """

        return str(self.event_manager.wait_for_event(event=event))

    # TODO: Add ask_to_gpt4 action, this way we can prompt a GPT-4 to obtain relevant info that we might need. All models should have access to this to get relevant info.
