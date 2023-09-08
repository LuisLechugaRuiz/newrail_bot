from abc import ABC
import inspect
import re
from typing import List, Optional

from newrail.agent.behavior.execution import Execution
from newrail.agent.communication.events.event_manager import EventManager
from newrail.agent.communication.requests.request_manager import RequestManager
from newrail.agent.config.config import AgentConfig
from newrail.capabilities.utils.helper import Helper
from newrail.capabilities.utils.decorators import (
    DEF_IS_ACTION,
    DEF_HAS_CONTEXT,
    DEF_HAS_QUESTION,
    DEF_SHOULD_SUMMARIZE,
)
from newrail.config.config import Config
from newrail.memory.utils.episodes.episode import Episode
from newrail.memory.utils.episodes.episode_manager import EpisodeManager
from newrail.organization.utils.logger.agent_logger import AgentLogger


def snake_case(name: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()


class Capability(ABC):
    def __init__(
        self,
        name: str,
        org_folder: str,
        agent_config: AgentConfig,
        event_manager: EventManager,
        request_manager: RequestManager,
        agent_logger: AgentLogger,
    ):
        self.name = name
        self.org_folder = org_folder
        self.agent_config = agent_config  # Used to access the agent configuration
        self.event_manager = event_manager  # Used to manage events
        self.request_manager = request_manager  # Used to manage requests
        self.episode_manager = EpisodeManager(
            agent_id=agent_config.id,
            team_id=agent_config.team_id,
            logger=agent_logger,
            tokens_percentage=Config().memory_goal_episodes_tokens_percentage,
        )
        self.last_question = None
        self.logger = agent_logger
        self.logger.create_logger(process_name=name, folder="Capability")

    @classmethod
    def get_name(cls) -> str:
        return snake_case(cls.__name__)

    @classmethod
    def get_description(cls) -> Optional[str]:
        return inspect.getdoc(cls)

    @classmethod
    def get_actions(cls) -> List[str]:
        return [
            name
            for name, method in inspect.getmembers(cls, inspect.isfunction)
            if getattr(method, DEF_IS_ACTION, False)
        ]

    @classmethod
    def get_context(cls) -> Optional[str]:
        for name, method in inspect.getmembers(cls, inspect.isfunction):
            if getattr(method, DEF_HAS_CONTEXT, False):
                return name

    @classmethod
    def get_action_doc(cls, action: str) -> Optional[str]:
        method = getattr(cls, action)
        doc = inspect.getdoc(method)
        if doc:
            # Remove empty lines from the doc
            description_lines = doc.splitlines()
            non_empty_lines = [line for line in description_lines if line.strip()]
            cleaned_description = "\n".join(non_empty_lines)
            return cleaned_description
        return None

    @classmethod
    def get_action_description(cls, action: str) -> Optional[str]:
        action_doc = cls.get_action_doc(action=action)
        # Split at "Args:"
        if action_doc:
            doc_parts = action_doc.split("Args:", 1)
            # Check if "Args:" was found in the docstring
            if len(doc_parts) == 2:
                description = doc_parts[0]
            else:
                # If "Args:" not found, return the full docstring
                description = action_doc
            return description
        return None

    @classmethod
    def get_action_arguments(cls, action: str) -> Optional[str]:
        action_doc = cls.get_action_doc(action=action)
        # Split at "Args:"
        if action_doc:
            doc_parts = action_doc.split("Args:", 1)
            # Check if "Args:" was found in the docstring
            if len(doc_parts) == 2:
                arguments = doc_parts[1]
            else:
                # If "Args:" not found, return None
                arguments = None
            return arguments
        return None

    @property
    def info(cls) -> Helper:
        return Helper(cls)

    @classmethod
    def get_info(cls) -> Helper:
        return Helper(cls)

    def has_action(self, action: str) -> bool:
        return hasattr(self, action)

    def should_summarize(self, action: str) -> bool:
        method = getattr(self, action)
        return getattr(method, DEF_SHOULD_SUMMARIZE, False)

    def get_question(self, action: str) -> Optional[str]:
        method = getattr(self, action)
        if getattr(method, DEF_HAS_QUESTION, False):
            last_question = self.last_question
            self.last_question = None
            return last_question
        return None

    def set_question(self, question: str) -> None:
        self.last_question = question

    def get_episode(
        self,
        execution: "Execution",
        observation: str,
    ) -> Episode:
        should_summarize = self.should_summarize(action=execution.action)
        question = None
        if should_summarize:
            question = self.get_question(action=execution.action)

        self.episode_manager.create_episodes(
            execution=execution,
            observation=observation,
            should_summarize=should_summarize,
        )
        # Create meta episode from all the previous episodes.
        meta_episode = self.episode_manager.create_meta_episode(
            question=question,
        )
        self.episode_manager.clear()
        return meta_episode


class BaseCapability(Capability):
    def __init__(
        self,
        capability_name: str,
        org_folder: str,
        agent_config: "AgentConfig",
        event_manager: "EventManager",
        request_manager: "RequestManager",
        agent_logger: "AgentLogger",
    ):
        super().__init__(
            capability_name=capability_name,
            org_folder=org_folder,
            agent_config=agent_config,
            event_manager=event_manager,
            request_manager=request_manager,
            agent_logger=agent_logger,
        )
