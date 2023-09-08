from newrail.agent.utils.mockeds.mocked_event_manager import (
    MockedEventManager,
)
from newrail.agent.utils.mockeds.mocked_request_manager import (
    MockedRequestManager,
)
from newrail.agent.utils.mockeds.mocked_logger import MockedLogger
from newrail.agent.utils.mockeds.mocked_agent_config import (
    MockedAgentConfig,
)


class MockedCapability:
    @classmethod
    def initialize(cls, plugin_name: str):
        event_manager = MockedEventManager(agent_name="testing agent")
        return {
            "plugin_name": plugin_name,
            "org_folder": "",
            "agent_config": MockedAgentConfig(agent_name="mocked_agent"),
            "event_manager": event_manager,
            "request_manager": MockedRequestManager(agent_name="mocked_agent"),
            "agent_logger": MockedLogger(agent_name="mocked_agent"),
        }
