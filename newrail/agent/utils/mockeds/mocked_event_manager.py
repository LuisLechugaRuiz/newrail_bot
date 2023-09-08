from newrail.agent.communication.events.event_manager import EventManager
from newrail.agent.utils.mockeds.mocked_agent_config import (
    MockedAgentConfig,
)
from newrail.agent.utils.mockeds.mocked_broker import MockedBroker


class MockedEventManager(EventManager):
    def __init__(self, agent_name: str):
        super().__init__(
            agent_config=MockedAgentConfig(agent_name=agent_name),
            broker=MockedBroker(agent_name=agent_name),
            supervisor_name="mocked_supervisor",
        )
