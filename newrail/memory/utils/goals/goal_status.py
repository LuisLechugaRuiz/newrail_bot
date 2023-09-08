from enum import Enum


class GoalStatus(Enum):
    NOT_STARTED = "Not started"
    IN_PROGRESS = "In Progress"
    SUCCEEDED = "Succeeded"
    FAILED = "Failed"

    def finished(self) -> bool:
        """Check if the goal has finished."""

        return self == GoalStatus.SUCCEEDED or self == GoalStatus.FAILED
