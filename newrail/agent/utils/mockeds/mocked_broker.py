from newrail.agent.communication.broker.broker import Broker
from newrail.agent.utils.mockeds.mocked_agent_config import (
    MockedAgentConfig,
)
from newrail.agent.utils.mockeds.mocked_logger import MockedLogger


class MockedBroker(Broker):
    def __init__(self, agent_name: str):
        super().__init__(
            agent_config=MockedAgentConfig(agent_name=agent_name),
            agent_logger=MockedLogger(agent_name=agent_name),
        )
