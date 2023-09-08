from datetime import datetime
from pydantic import Field
from typing import Tuple

from newrail.memory.utils.goals.goal import Goal
from newrail.memory.utils.thought.thought import Thought
from newrail.organization.utils.logger.agent_logger import AgentLogger
from newrail.parser.loggable_base_model import LoggableBaseModel
from newrail.parser.pydantic_parser import (
    get_format_instructions,
)
from newrail.parser.chat_parser import ChatParser

PLAN_PROMPT = """
Current time is: {time}.
You are {agent_name}, your mission is: {agent_mission}
Your responsibility is to continually manage a prioritized sequence of goals that direct your actions towards accomplishing the given task.
These goals should be sequenced from the highest to lowest priority, with each goal acting as a feasible step towards task completion, given your available capabilities.
Additionally, you are required to identify a central topic and design a query associated with it.
The search_query will be used to search relevant information from previous experiences and provide the pertinent context during the execution of the action tied to the highest priority goal.

===== CURRENT TASK =====
This is your current task:
{task}

==== GOALS =====
Here are the goals that you updated before last action:
{goals}

Using the information above, please update your goals for the current task.

==== SHORT TERM MEMORY =====
Here is a summary of the actions you have executed so far:
{summary}

==== LAST ACTION =====
Here is the result of the last action you executed:
{last_episode}

===== EVENTS =====
These are new events that have taken place while the previous goal was being accomplished, consider them when updating your goals:
{events}

==== RELEVANT INFORMATION =====
Here is relevant information extracted from your long term memory:
{relevant_information}

===== AVAILABLE CAPABILITIES =====
These are the capabilities that you have available:
{capabilities_description}

The capabilities above are the only ones that you can use to accomplish your goals.
Is very important that you verify that the capability selected for each goal can be used to accomplish it, for this verify that the actions can be used to accomplish the goal.

===== OUTPUT INSTRUCTIONS =====
{format_instructions}
"""


class Plan(LoggableBaseModel):
    goals: list[Goal] = Field(
        description="The updated list of goals that you should work on, consider prevoius goals and update them based on new information"
    )
    search_queries: list[str] = Field(
        description="A list of queries that need to be answered in order to retrieve the relevant context for the execution of the action tied to the highest priority goal"
    )

    @classmethod
    def get_plan(
        cls,
        agent_name,
        agent_mission,
        task,
        goals,
        previous_thought,
        summary,
        last_episode,
        events,
        relevant_information,
        capabilities_description,
        logger: AgentLogger,
    ) -> Tuple[Thought, "Plan"]:
        plan = PLAN_PROMPT.format(
            time=datetime.now().time(),
            agent_name=agent_name,
            agent_mission=agent_mission,
            task=task,
            goals=goals,
            previous_thought=previous_thought,
            summary=summary,
            last_episode=last_episode,
            events=events,
            relevant_information=relevant_information,
            capabilities_description=capabilities_description,
            format_instructions=get_format_instructions([Thought, Plan]),
        )
        logger.log(plan, should_print=False)
        plan_response = ChatParser(logger=logger).get_parsed_response(
            system=plan,
            user="Remember to answer using the output format to provide a Plan!",
            containers=[Thought, Plan],
            smart_llm=True,
        )
        return plan_response[0], plan_response[1]

    def finished(self):
        """Check if all the goals have been accomplished."""

        for goal in self.goals:
            if not goal.finished():
                return False
        return True

    def __str__(self):
        plan = "Plan:\n\n"
        for goal in self.goals:
            plan = plan + goal.get_description() + "\n"
        for search_query in self.search_queries:
            plan = plan + f"\nSearch query: {search_query}\n"
        return plan
