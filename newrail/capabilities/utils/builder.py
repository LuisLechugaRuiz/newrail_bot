import importlib
import inspect
import os
import re
from typing import Callable, Dict, Optional, Type, TYPE_CHECKING

from newrail.capabilities.capability import BaseCapability, Capability
from newrail.agent.behavior.execution import Execution

if TYPE_CHECKING:
    from newrail.agent.communication.events.event_manager import (
        EventManager,
    )
    from newrail.agent.communication.requests.request_manager import (
        RequestManager,
    )
    from newrail.agent.config.config import AgentConfig
    from newrail.organization.utils.logger.agent_logger import AgentLogger


DEF_PROTECTED_CLASSES = [BaseCapability, Capability]


class CapabilityBuilder:
    """
    The CapabilityBuilder class is responsible for loading capabilities and building instances of the
    corresponding classes.

    Example usage:

    1. Load capabilities from a folder:
        CapabilityBuilder.load_capabilities("path/to/your/capabilities/folder")

    2. Get a capability instance:
        plugin_instance = CapabilityBuilder.get_plugin(
            plugin_name="your_plugin_name",
            org_folder="your_organization_folder",
            agent_logger=your_agent_logger_instance,
        )

    3. Get an action from a capability instance:
        action = CapabilityBuilder.get_action(
            org_folder="your_organization_folder",
            agent_logger=your_agent_logger_instance,
            capability=plugin_instance,
            execution=your_execution_instance,
        )
    """

    CAPABILITIES: Dict[str, Type[Capability]] = {}

    @classmethod
    def get_capability(
        cls,
        name: str,
        org_folder: str,
        agent_config: "AgentConfig",
        event_manager: "EventManager",
        request_manager: "RequestManager",
        agent_logger: "AgentLogger",
    ) -> Capability:
        plugin_instance = cls.CAPABILITIES.get(name)

        if plugin_instance is None:
            raise ValueError(
                f"Unknown capability: {name}, please verify the capability name!"
            )

        return plugin_instance(
            name=name,
            org_folder=org_folder,
            agent_config=agent_config,
            event_manager=event_manager,
            request_manager=request_manager,
            agent_logger=agent_logger,
        )

    @classmethod
    def get_action(
        cls,
        org_folder: str,
        agent_config: "AgentConfig",
        event_manager: "EventManager",
        request_manager: "RequestManager",
        agent_logger: "AgentLogger",
        capability: Capability,
        execution: Execution,
    ) -> Callable:
        # Get the capability instance from the capabilities.
        plugin_instance = cls.get_capability(
            name=capability.name,
            org_folder=org_folder,
            agent_config=agent_config,
            event_manager=event_manager,
            request_manager=request_manager,
            agent_logger=agent_logger,
        )

        # Update the arguments.
        return execution.update_arguments_from_proxy_value(target_self=plugin_instance)

    @classmethod
    def load_capabilities(cls, folder: Optional[str] = None):
        if folder is None:
            capabilities_folder = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "capabilities",
            )
            capability_package = (
                __package__.split(".")[0] + ".capabilities.capabilities"
            )
        for root, _, files in os.walk(capabilities_folder):
            relative_path = os.path.relpath(root, capabilities_folder).replace(
                os.path.sep, "."
            )
            for file in files:
                if file.endswith(".py") and not file.startswith("__"):
                    module_name = file[:-3]
                    # Create a module path
                    module_path = (
                        f"{capability_package}.{relative_path}.{module_name}"
                        if relative_path != "."
                        else f"{capability_package}.{module_name}"
                    )
                    # Import the module
                    module = importlib.import_module(module_path)

                    # Validate the docstring of the capability.
                    for _, sub_cls in inspect.getmembers(module, inspect.isclass):
                        if (
                            issubclass(sub_cls, Capability)
                            and sub_cls not in DEF_PROTECTED_CLASSES
                        ):
                            actions = sub_cls.get_actions()

                            for action in actions:
                                description = sub_cls.get_action_description(action)
                                try:
                                    cls.validate_google_style_docstring(description)
                                except ValueError as e:
                                    raise ValueError(
                                        f"Invalid description at docstring for action '{action}': {e}"
                                    )
                                arguments = sub_cls.get_action_arguments(action)
                                try:
                                    cls.validate_google_style_docstring(arguments)
                                except ValueError as e:
                                    raise ValueError(
                                        f"Invalid arguments at docstring for action '{action}': {e}"
                                    )
                            CapabilityBuilder.CAPABILITIES[sub_cls.get_name()] = sub_cls

    @classmethod
    def validate_google_style_docstring(cls, docstring: Optional[str]) -> None:
        if docstring is None:
            raise ValueError("Docstring is missing.")

        # Split the docstring by lines and remove leading/trailing whitespaces
        lines = [line.strip() for line in docstring.strip().splitlines()]

        # Check if there's at least one non-empty line
        if len(lines) < 1 or not lines[0]:
            raise ValueError("Docstring must have at least one non-empty line.")

        # Check for the Args section (if present)
        has_args_section = any(line.startswith("Args:") for line in lines)

        # Define regular expressions for argument type patterns
        arg_pattern = re.compile(r"^\s*\w+\s*\([\w\[\], ]+\):\s*.+")

        if has_args_section:
            arg_section_start = lines.index("Args:")
            for line in lines[arg_section_start + 1 :]:
                if line.startswith("Returns:"):
                    break
                if not line:  # Skip empty lines
                    continue
                if not arg_pattern.match(line):
                    raise ValueError(f"Invalid argument format in docstring: {line}")
