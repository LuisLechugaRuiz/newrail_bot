from newrail.agent.communication.requests.request_manager import RequestManager
from newrail.agent.utils.mockeds.mocked_agent_config import (
    MockedAgentConfig,
)
from newrail.agent.utils.mockeds.mocked_broker import (
    MockedBroker,
)


class MockedRequestManager(RequestManager):
    def __init__(self, agent_name: str):
        super().__init__(
            agent_config=MockedAgentConfig(agent_name=agent_name),
            broker=MockedBroker(agent_name=agent_name),
        )
