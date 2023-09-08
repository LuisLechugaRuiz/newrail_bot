import unittest

from newrail.agent.behavior.execution import Execution
from newrail.agent.utils.mockeds.mocked_event_manager import (
    MockedEventManager,
)
from newrail.agent.utils.mockeds.mocked_logger import MockedLogger
from newrail.capabilities.utils.builder import CapabilityBuilder


class BuilderTest(unittest.TestCase):
    def test_execution(self):
        # We do this at the start.
        CapabilityBuilder.load_capabilities()

        for capability in CapabilityBuilder.CAPABILITIES:
            print("capability:", capability)

        # Then we load the data also to Weaviate here
        # TODO: Ingest action data there.

        # On planning we select the capability to use so this would be an answer:
        capability_name = "programmer"
        # On execution we get the action that he want to execute from the repertoire
        action = Execution(
            name="execute_python_file",
            arguments={"file": "hello_world.py"},
        )
        # Other example:
        # capability_name = "shell_executor"
        # action = Action(
        #    name="execute_shell",
        #    arguments={"command_line": "mkdir hello_luis"},
        # )

        # Now we can do this way to get the action or use the same than execute at Agent.
        agent_name = "TestAgent"
        mock_logger = MockedLogger(agent_name=agent_name)
        event_manager = MockedEventManager(
            agent_name=agent_name,
        )

        mock_org_folder = "."
        capability = CapabilityBuilder.get_capability(
            name=capability_name,
            org_folder=mock_org_folder,
            event_manager=event_manager,
            agent_logger=mock_logger,
        )
        # Used on manager to select the right capability.
        print(
            "Non detailed description used on manager to select the right capability:\n\n"
            + capability.info.high_level_description(detailed=False)
        )
        # Used during planning to select the right action.
        print(
            "\nDetailed description used during planning to select the right action.:\n\n"
            + capability.info.high_level_description(detailed=True)
        )
        action = CapabilityBuilder.get_action(
            org_folder=mock_org_folder,
            event_manager=event_manager,
            agent_logger=mock_logger,
            capability=capability,
            action=action,
        )
        # Used during execution to obtain the arguments.
        print(
            "\nLow level description used during execution to obtain the arguments:\n\n"
            + capability.info.low_level_description()
        )
        self.assertTrue("Hello World, I'm NewRail." in action())  # Lets go!!!


if __name__ == "__main__":
    unittest.main()
