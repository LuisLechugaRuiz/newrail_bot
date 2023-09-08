from datetime import datetime
from typing import Any, Callable, Dict, Tuple
from pydantic import Field, PrivateAttr

from newrail.memory.utils.thought.thought import Thought
from newrail.organization.utils.logger.agent_logger import AgentLogger
from newrail.parser.chat_parser import ChatParser
from newrail.parser.pydantic_parser import (
    get_format_instructions,
)
from newrail.parser.loggable_base_model import LoggableBaseModel

# TODO: Create template which include general data such as time or output instructions
ACTION_PROMPT = """
Current time: {time}
You are {agent_name}. Your task is to use the information provided below to fill the arguments of the selected action that you will execute to accomplish your goal.

===== TASK =====
This is your current task:
{task}

===== GOAL =====
This is the goal that you are trying to accomplish:
{goal}

===== PREVIOUS THOUGHT =====
This is your previous thought, keep in mind that it can contain future actions that you have not yet executed:
{previous_thought}

===== ACTION DESCRIPTION =====
Review the detailed description of the action to fill the arguments in their proper format:
{action_description}

==== RELEVANT INFORMATION =====
Here is relevant information extracted from your memory:
{relevant_information}

===== OUTPUT INSTRUCTIONS =====
{format_instructions}
"""


class Execution(LoggableBaseModel):
    action: str = Field(
        description="The name of the appropriate action that should be used to fulfill the current step. Remember to DON'T REPEAT ACTIONS"
    )
    arguments: Dict[str, Any] = Field(
        description="A dictionary with the action arguments where keys and values are both strings, e.g., {'arg1': 'value1', 'arg2': 'value2'}. You must provide the EXACT arguments (as declared in 'Args' section of each action) with their expected format that the action requires. Failure to do so will prevent the action from executing correctly!"
    )
    _capability: str = PrivateAttr(default=None)

    def get_full_command(self):
        return f"Action: {self.action} with args: {self.arguments}"

    def get_capability(self):
        return self._capability

    def update_arguments_from_proxy_value(self, target_self: Any) -> Callable:
        """This function updates the values of a target function with the values of arguments members.
        Moving this way the info from the action obtained from the LLM response to our
        local object."""

        # Get the target function from the target_self object
        function = getattr(target_self, self.action)

        # Create a lambda function to call the original function with the arguments from self.arguments
        if function:
            return lambda: function(**self.arguments)
        else:
            raise ValueError(f"Unknown action: {self.action}")

    def set_capability(self, capability: str):
        self._capability = capability

    @classmethod
    def get_execution(
        cls,
        agent_name: str,
        task: str,
        goal: str,
        previous_thought: str,
        action_description: str,
        relevant_information: str,
        logger: AgentLogger,
    ) -> Tuple[Thought, "Execution"]:
        action_prompt = ACTION_PROMPT.format(
            time=datetime.now().isoformat(),
            agent_name=agent_name,
            task=task,
            goal=goal,
            previous_thought=previous_thought,
            action_description=action_description,
            relevant_information=relevant_information,
            format_instructions=get_format_instructions([Thought, Execution]),
        )
        logger.log(action_prompt, should_print=False)
        action_response = ChatParser(logger=logger).get_parsed_response(
            system=action_prompt,
            user="Remember to answer using the output format to provide a Thought and an Execution!",
            containers=[Thought, Execution],
            smart_llm=True,
        )
        return action_response[0], action_response[1]

    def to_dict(self):
        return {
            "action": self.action,
            "arguments": self.arguments,
            "_capability": self._capability,
        }

    @classmethod
    def from_dict(cls, data):
        return cls(**data)
