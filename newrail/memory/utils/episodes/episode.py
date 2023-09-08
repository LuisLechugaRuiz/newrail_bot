from datetime import datetime
from pydantic import Field, PrivateAttr
from typing import List, Optional
from newrail.parser.loggable_base_model import LoggableBaseModel
from newrail.parser.pydantic_parser import (
    get_format_instructions,
)
from newrail.memory.utils.episodes.prompts.meta_episode_prompt import (
    DEF_META_EPISODE_PROMPT,
)
from newrail.memory.utils.episodes.prompts.guided_meta_episode_prompt import (
    DEF_GUIDED_META_EPISODE_PROMPT,
)
from newrail.memory.utils.episodes.prompts.summarized_episode_prompt import (
    DEF_SUMMARIZED_EPISODE_PROMPT,
)
from newrail.memory.utils.episodes.prompts.raw_episode_prompt import (
    DEF_RAW_EPISODE_PROMPT,
)
from newrail.utils.print_utils import indent


class Overview(LoggableBaseModel):
    overview: str = Field(
        description="A brief, high-level summary of the episode's content. It provides a quick snapshot of what the episode encompasses without diving into details."
    )

    @classmethod
    def get_raw_episode_prompt(
        cls,
        task_description: str,
        action: str,
        observation: str,
        max_overview_tokens: int,
    ):
        return DEF_RAW_EPISODE_PROMPT.format(
            task_description=task_description,
            action=action,
            observation=observation,
            max_overview_tokens=max_overview_tokens,
            format_instructions=get_format_instructions([Overview]),
        )


class Episode(LoggableBaseModel):
    content: str = Field(
        description="A summary which incorporate all crucial details including, but not limited to, relevant citations, names, links, and any other pertinent information."
    )
    overview: str = Field(
        description="A brief, high-level summary of the episode's content. It provides a quick snapshot of what the episode encompasses without diving into details."
    )
    _creation_time: str = PrivateAttr(default="")
    _capability: str = PrivateAttr(default="")
    _action: str = PrivateAttr(default="")
    _uuid: Optional[str] = PrivateAttr(default=None)
    _child_episodes: List["Episode"] = PrivateAttr(default=[])
    _order: int = PrivateAttr(default=0)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._creation_time = datetime.now().isoformat(timespec="seconds")

    def add_child_episodes(self, episodes: List["Episode"]):
        self._child_episodes.extend(episodes)

    def link_to_uuid(self, uuid):
        self._uuid = uuid

    def set_order(self, order):
        self._order = order

    def set_tool(self, capability, action):
        self._capability = capability
        self._action = action

    def get_uuid(self):
        return self._uuid

    def get_description(self, include_child_episodes=False):
        description = f"- {self._creation_time}: Overview: {self.overview}\nContent: {self.content}"
        if self._child_episodes and include_child_episodes:
            child_episodes_overview = "\n".join(
                [
                    indent(text=episode.get_overview())
                    for episode in self._child_episodes
                ]
            )
            description += f"\nChild Episodes:\n{child_episodes_overview}"
        return description

    def get_overview(self, show_uuid=True):
        if show_uuid:
            return f"- {self._creation_time}: {self.overview} (UUID: {self._uuid})"
        return self.overview

    def to_dict(self):
        return {
            "content": self.content,
            "overview": self.overview,
            "creation_time": self._creation_time,
            "capability": self._capability,
            "action": self._action,
            "uuid": self._uuid,
            "child_episodes": [episode.to_dict() for episode in self._child_episodes],
            "order": self._order,
        }

    @classmethod
    def from_dict(cls, data):
        cls = Episode(
            content=data["content"],
            overview=data["overview"],
            _creation_time=data["creation_time"],
            _capability=data["capability"],
            _action=data["action"],
            _uuid=data["uuid"],
            _child_episodes=[
                Episode.from_dict(episode) for episode in data["child_episodes"]
            ],
            _order=data["order"],
        )
        cls.link_to_uuid(data["uuid"])
        return cls

    @classmethod
    def get_summarized_episode_prompt(
        cls,
        task_description: str,
        action: str,
        observation: str,
        max_overview_tokens: int,
        max_content_tokens: int,
    ):
        return DEF_SUMMARIZED_EPISODE_PROMPT.format(
            task_description=task_description,
            action=action,
            observation=observation,
            max_overview_tokens=max_overview_tokens,
            max_content_tokens=max_content_tokens,
            format_instructions=get_format_instructions([Episode]),
        )

    @classmethod
    def get_meta_episode_prompt(
        cls,
        task_description: str,
        previous_content: str,
        episodes: str,
        max_tokens: int,
    ):
        return DEF_META_EPISODE_PROMPT.format(
            task_description=task_description,
            previous_content=previous_content,
            new_content=episodes,
            max_tokens=max_tokens,
            format_instructions=get_format_instructions([Episode]),
        )

    @classmethod
    def get_guided_meta_episode_prompt(
        cls,
        task_description: str,
        previous_content: str,
        episodes: str,
        question: str,
        max_tokens,
    ):
        return DEF_GUIDED_META_EPISODE_PROMPT.format(
            task_description=task_description,
            question=question,
            previous_content=previous_content,
            new_content=episodes,
            max_tokens=max_tokens,
            format_instructions=get_format_instructions([Episode]),
        )
