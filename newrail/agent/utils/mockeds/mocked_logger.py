from newrail.agent.utils.mockeds.mocked_agent_config import (
    MockedAgentConfig,
)
from newrail.organization.utils.logger.agent_logger import AgentLogger


class MockedLogger(AgentLogger):
    def __init__(
        self,
        agent_name: str,
    ):
        super().__init__(
            agent_name, MockedAgentConfig(agent_name=agent_name), "", "mocked_logger"
        )
