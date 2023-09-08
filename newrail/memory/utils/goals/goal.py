from typing import Any
from pydantic import Field, PrivateAttr

from newrail.memory.utils.goals.goal_status import GoalStatus
from newrail.parser.loggable_base_model import LoggableBaseModel


class Goal(LoggableBaseModel):
    description: str = Field("The description of the goal.")
    capability: str = Field(
        "The capability that should be used to achieve the goal should be one of the available capabilities, is very important that you verify that the goal can be achieved using this capability."
    )
    action: str = Field(
        "The action that should be performed to achieve the goal this action should be listed on the actions section of the selected capabilities, is very important that you verify that the goal can be achieved using this action."
    )
    validation_condition: str = Field(
        "The condition that should be met to validate the goal. It should be used as a post-condition for current goal and pre-condition for the next goal. E.g: 'The file 'x' is created properly.'"
    )
    # TODO: Do we need it?
    _status: GoalStatus = PrivateAttr(default=GoalStatus.NOT_STARTED)

    def get_description(self) -> str:
        """Get a human-readable description of the current goal"""

        return f"Description: {self.description}\nCapability: {self.capability}\nAction: {self.action}\nValidation condition: {self.validation_condition}\n"

    def get_status(self) -> GoalStatus:
        """Get the status of the goal"""

        return self._status

    def update_status(self, status: GoalStatus) -> None:
        """Update the status of the goal"""

        self._status = status

    def to_dict(self) -> dict[str, Any]:
        """Method used to serialize the goal"""

        return {
            "description": self.description,
            "action": self.action,
            "capability": self.capability,
            "validation_condition": self.validation_condition,
            "status": self._status.name,
        }

    def finished(self) -> bool:
        """Check if the goal has finished."""

        return self._status.finished()

    @classmethod
    def from_dict(cls, data):
        return cls(
            description=data["description"],
            capability=data["capability"],
            action=data["action"],
            validation_condition=data["validation_condition"],
            _status=data["status"],
        )
