from datetime import datetime
from pydantic import Field

from newrail.parser.chat_parser import ChatParser
from newrail.parser.loggable_base_model import LoggableBaseModel
from newrail.parser.pydantic_parser import (
    get_format_instructions,
)
from newrail.organization.utils.logger.agent_logger import AgentLogger

ATTENTION_INITIAL_PROMPT = """
Current time is: {time}.
Your task is to provide the relevant information needed to perform the next action. It should be very detailed. Keep in mind that the relevant information that you provide will be the only information available during the execution so you should ensure that it contains all the information needed to perform the next action.

To fill the relevant information combine the information from the different episodes and answer the questions presented at EPISODES section.

Ensure that all the info needed to perform the next action is available in the relevant information field, in case some info from previous episodes might be relevant you can use the 'remember_episode' field to provide the UUID of the episode that you want to remember.
The 'remember_episode' is specially useful to obtain full content of previous episodes, e.g: The agent read a file (or navigated to a web) and you want to remember the content of the file to use it in the next action.

===== GOAL =====
Current goal:
{goal}

===== ACTION =====
Capability: {capability}
Action: {action}

===== THOUGHT =====
Your current thought:
{thought}

===== EPISODES =====
Here is a ordered sequence with the overviews of the most recent episodes:
{recent_episodes}

In case you want to obtain the full content of any of the previous episodes you should fill the 'remember_episode' field with the UUID of the episode.

This is the full content of the most recent episode:
{most_recent_episode}

These are the questions that you should answer to fill the relevant relevant information. Here are the questions with the most similar episode gathered from the episodic memory:
{most_similar_episodes}

===== OUTPUT INSTRUCTIONS =====
Leave the 'remember_episode' and 'search_query' fields as None if you have enough information to perform the next action.

In case you don't have enough information you can iterate again filling the 'search_query' field with a query that will be used to retrieve relevant information from the semantic memory. 
Use this with caution, you should only iterate if you are sure that you don't have enough information to perform the next action.

{format_instructions}
"""

ATTENTION_ITERATION_PROMPT = """
Current time is: {time}.
Your task is to provide the relevant information needed to perform the next action.

To fill the relevant information combine the information from the different episodes to answer the questions presented at EPISODES section, use also the information presented at RELEVANT INFORMATION section as it was added from previous iterations.
Ensure that all the info needed to perform the next action is available in the relevant information field, in case some info from previous episodes might be relevant you can use the 'remember_episode' field to provide the UUID of the episode that you want to remember.

===== GOAL =====
Current goal:
{goal}

===== ACTION =====
Capability: {capability}
Action: {action}

===== THOUGHT =====
Your current thought:
{thought}

===== EPISODES =====
This is the episode that you decided to remember:
{remembered_episode}

These are the questions that you should answer to fill the relevant relevant information. Here are the questions with the most similar episode gathered from the episodic memory:
{most_similar_episodes}

In case you want to see the full episode of any of the linked episodes you should fill the 'remember_episode' field with the UUID of the episode.

===== RELEVANT INFORMATION =====
This is the relevant information stored you stored during the previous iterations, do not delete it unless you are sure it is not relevant anymore:
{relevant_information}

===== OUTPUT INSTRUCTIONS =====
Leave the 'remember_episode' and 'search_query' fields as None if you have enough information to perform the next action.

In case you don't have enough information you can iterate again filling the 'search_query' field with a query that will be used to retrieve relevant information from the semantic memory. 
Use this with caution, you should only iterate if you are sure that you don't have enough information to perform the next action.

{format_instructions}
"""


class Attention(LoggableBaseModel):
    relevant_information: str = Field(
        description="ALL the information needed to perform the next action. The information should be very detailed and it should be a combination of the information from the different episodes to answer the questions presented at EPISODES section."
    )
    remember_episode_uuid: str = Field(
        description="The UUID of the episode that should be remembered, leave it as an empty string if you have enough information to perform the next action."
    )
    search_query: str = Field(
        description="A query that will be used to retrieve relevant information from the semantic memory, leave it as an empty string if you have enough information to perform the next action."
    )

    @classmethod
    def get_relevant_memory(
        cls,
        goal: str,
        capability: str,
        action: str,
        thought: str,
        recent_episodes: str,
        most_recent_episode: str,
        most_similar_episodes: str,
        logger: AgentLogger,
    ) -> "Attention":
        attention_prompt = ATTENTION_INITIAL_PROMPT.format(
            time=datetime.now().isoformat(),
            goal=goal,
            capability=capability,
            action=action,
            thought=thought,
            recent_episodes=recent_episodes,
            most_recent_episode=most_recent_episode,
            most_similar_episodes=most_similar_episodes,
            format_instructions=get_format_instructions([Attention]),
        )
        logger.log(attention_prompt, should_print=False)
        attention_response = ChatParser(logger=logger).get_parsed_response(
            system=attention_prompt,
            user="Remember to answer using the output format to provide a Attention!",
            containers=[Attention],
            smart_llm=True,
        )
        return attention_response[0]

    @classmethod
    def get_relevant_memory_iterative(
        cls,
        goal: str,
        capability: str,
        action: str,
        thought: str,
        remembered_episode: str,
        most_similar_episodes: str,
        relevant_information: str,
        logger: AgentLogger,
    ) -> "Attention":
        attention_prompt = ATTENTION_ITERATION_PROMPT.format(
            time=datetime.now().isoformat(),
            goal=goal,
            capability=capability,
            action=action,
            thought=thought,
            remembered_episode=remembered_episode,
            most_similar_episodes=most_similar_episodes,
            relevant_information=relevant_information,
            format_instructions=get_format_instructions([Attention]),
        )
        logger.log(attention_prompt, should_print=False)
        attention_response = ChatParser(logger=logger).get_parsed_response(
            system=attention_prompt,
            user="Remember to answer using the output format to provide a Attention!",
            containers=[Attention],
            smart_llm=True,
        )
        return attention_response[0]
