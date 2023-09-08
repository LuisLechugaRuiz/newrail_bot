from typing import Any, Callable, List

from newrail.memory.utils.thought.thought import Thought
from newrail.utils.token_counter import count_string_tokens
from newrail.config.config import Config


class ThoughtBuffer:
    def __init__(
        self,
        on_limit_reached: Callable,
        min_token_threshold: int = Config().thoughts_min_tokens,
        max_token_threshold: int = Config().thoughts_max_tokens,
    ):
        self.thoughts: List[Thought] = []
        self.on_limit_reached = on_limit_reached
        self.min_token_threshold = min_token_threshold
        self.max_token_threshold = max_token_threshold

    def add_thought(self, thought: Thought) -> None:
        """Add a new episode, convert into meta episode if needed."""

        self.thoughts.append(thought)
        if self.get_tokens_count() > self.max_token_threshold:
            self.on_limit_reached()
            while (
                self.get_tokens_count() > self.min_token_threshold
                and len(self.thoughts) > 1
            ):
                self.thoughts.pop(0)

    def clear(self) -> None:
        """Clear current thoughts"""

        self.thoughts = []

    def get_thoughts_str(self) -> str:
        """Get thoughts string"""

        return "\n".join(thought.get_description() for thought in self.thoughts)

    def get_tokens_count(self) -> int:
        """Get the tokens count of the summaries"""

        return count_string_tokens(self.get_thoughts_str())

    def to_dict(self) -> dict[str, Any]:
        """Buffer to dict"""

        return {
            "thoughts": [thought.to_dict() for thought in self.thoughts],
        }

    @classmethod
    def from_dict(cls, on_limit_reached_callback, data):
        """From dict"""

        thought_buffer = cls(on_limit_reached=on_limit_reached_callback)
        for thought_data in data["thoughts"]:
            thought = Thought.from_dict(data=thought_data)
            thought_buffer.add_thought(thought)
        return thought_buffer
