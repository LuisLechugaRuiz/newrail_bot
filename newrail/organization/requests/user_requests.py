from pydantic import Field

from newrail.parser.loggable_base_model import LoggableBaseModel


class UserRequest:
    user_id: str = Field(description="The user id.")
    user_name: str = Field(description="The user name.")


class MaxIterationsRequest(UserRequest, LoggableBaseModel):
    iterations: int = Field(description="The number of iterations.")


class ChatRequest(UserRequest, LoggableBaseModel):
    agent_name: str = Field(description="The agent name.")
    message: str = Field(description="The message to send to the agent.")


class UpdateProtagonist(UserRequest, LoggableBaseModel):
    agent_name: str = Field(description="The agent name.")
