import json
import os
from typing import Dict, List, Optional

from newrail.agent.communication.events.event import Event
from newrail.memory.utils.goals.goal_memory import GoalMemory
from newrail.memory.utils.goals.goal import Goal
from newrail.memory.utils.episodes.episode import Episode
from newrail.memory.utils.episodes.episode_manager import EpisodeManager
from newrail.memory.utils.thought.thought import Thought
from newrail.memory.utils.task.task import Task
from newrail.memory.utils.task.task_memory import TaskMemory
from newrail.organization.utils.logger.agent_logger import AgentLogger


class EpisodicMemory:
    def __init__(
        self,
        agent_id: str,
        team_id: str,
        folder: str,
        logger: AgentLogger,
    ):
        self.file_path = os.path.join(folder, "episodic_memory.json")
        self.agent_id = agent_id
        self.team_id = team_id
        self.folder = folder
        self.logger = logger.create_logger("episodic_memory")
        loaded = False
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, "r") as f:
                    data = json.load(f)
                    self.load(data=data)
                    goal = self.goal_memory.get_current_goal()
                    loaded = True
                    if goal:
                        self.logger.log(f"Starting episodic memory on goal: {goal}")
                    self.logger.log("Starting existing episodic memory without goal.")
            except Exception as e:
                self.logger.log(f"Error loading episodic memory: {e}")
        if not loaded:
            self.start_new_memory()
        self.save()

    def add_event(self, event: Event) -> None:
        """Add event to current episode"""

        self.events.append(event)

    def add_episode(self, episode: Episode) -> None:
        """Add episode to current episode"""

        self.episode_manager.add_episode(episode=episode)

    def add_goal_episode(self, episode: Episode) -> None:
        """Add episode to current episode"""

        self.goal_memory.add_episode(episode=episode)

    def clear_events(self) -> None:
        """Clear events"""

        self.events = []

    def add_task(self, task: Task):
        """Add a new task"""

        self.task_memory.add_task(task=task)
        self.save()

    def get_current_goal(self) -> Optional[Goal]:
        """Get current goal"""

        return self.goal_memory.get_current_goal()

    def get_events(self) -> List[Event]:
        """Get events"""

        return self.events

    # TODO: Think about changing thought as propose by GPT-4: Concept, elaboration and evaluation
    def get_thought(self) -> Thought:
        """Get thought"""

        return self.thought

    def get_task(self) -> Optional[Task]:
        """Get task"""

        return self.task_memory.get_task()

    def get_episodes(self) -> List[Episode]:
        """Get previous episodes"""

        return self.episode_manager.get_episodes()

    def get_goal_episodes(self) -> List[Episode]:
        """Get previous episodes"""

        return self.goal_memory.get_goal_episodes()

    # TODO: Rename
    def get_last_episode(self) -> Optional[Episode]:
        return self.goal_memory.get_last_episode()

    def get_goals(self) -> List[Goal]:
        """Get goals"""

        return self.goal_memory.get_goals()

    # TODO: Do we need this?
    def get_working_memory_episodes_uuid(self) -> List[str]:
        """Get the uuid of the working memory episodes"""

        episodes_uuid = []
        for episode in self.goal_memory.get_goal_episodes():
            episode_uuid = episode.get_uuid()
            if not episode_uuid:
                raise Exception(f"Episode {episode.overview} without uuid!")
            episodes_uuid.append(episode_uuid)
        return episodes_uuid

    def get_episodic_memory(self) -> str:
        """Get episodic memory"""

        previous_episodes = self.episode_manager.get_episodes_str()
        if previous_episodes:
            return previous_episodes
        return "No previous goals achieved yet."

    def get_evaluation(self) -> str:
        """Get evaluation"""

        return self.goal_memory.get_evaluation()

    def get_similar_episodes(self) -> Dict[str, Episode]:
        """Get most similar episode"""

        return self.similar_episodes

    def get_relevant_information(self) -> str:
        return self.relevant_information

    def max_iterations_reached(self) -> bool:
        """Return True if max iterations reached."""

        return self.goal_memory.max_iterations_reached()

    def on_goal_accomplished(self) -> Optional[Episode]:
        """Called when a goal is accomplished"""

        self.goal_memory.on_goal_finished()
        episode = self.goal_memory.create_meta_episode()
        if episode:
            self.add_episode(episode=episode)

    def set_goals(self, goals: List[Goal]) -> None:
        if len(goals) > 0:
            self.goal_memory.set_goals(goals=goals)
            self.episode_manager.set_current_goal(current_goal=goals[0].description)
            self.save()

    def update_similar_episodes(self, similar_episodes: Dict[str, Episode]) -> None:
        """Update most similar episode"""

        self.similar_episodes = similar_episodes
        self.save()

    def update_relevant_information(self, relevant_information: str) -> None:
        self.relevant_information = relevant_information
        self.save()

    def update_thought(self, thought: Thought) -> None:
        """Update last thought"""

        self.thought = thought
        self.save()

    def load(self, data):
        """Load the data from a dict"""

        self.thought = Thought.from_dict(data=data["thought"])
        self.events = [Event.from_dict(data=event) for event in data["events"]]
        self.episode_manager = EpisodeManager.from_dict(
            data=data["episode_manager"], logger=self.logger
        )
        self.goal_memory = GoalMemory.from_dict(
            data=data["goal_memory"], logger=self.logger
        )
        self.similar_episodes = {
            str(query): Episode.from_dict(data=episode)
            for query, episode in data["similar_episodes"].items()
        }
        self.task_memory = TaskMemory.from_dict(data["task_memory"])
        self.relevant_information = data["relevant_information"]

    def save(self):
        episodic_memory_dict = self.to_dict()

        with open(self.file_path, "w") as f:
            f.write(json.dumps(episodic_memory_dict, indent=2))

    def to_dict(self):
        return {
            "thought": self.thought.to_dict(),
            "events": [event.to_dict() for event in self.events],
            "similar_episodes": [
                [query, episode.to_dict()]
                for query, episode in self.similar_episodes.items()
            ],
            "goal_memory": self.goal_memory.to_dict(),
            "episode_manager": self.episode_manager.to_dict(),
            "task_memory": self.task_memory.to_dict(),
            "relevant_information": self.relevant_information,
        }

    def set_task_finished(self):
        self.task_memory.set_task_finished()
        self.save()

    def start_new_memory(self):
        self.thought = Thought(
            text="No text yet",
            reasoning="No reasoning yet",
            criticism="No criticism yet",
        )
        self.events: List[Event] = []
        self.goal_memory = GoalMemory(
            agent_id=self.agent_id, team_id=self.team_id, logger=self.logger
        )
        self.episode_manager = EpisodeManager(
            agent_id=self.agent_id,
            team_id=self.team_id,
            logger=self.logger,
        )
        self.similar_episodes: Dict[str, Episode] = {}
        self.relevant_information = ""
        # TODO: We can do a priority queue but we need extra logic to evalute the priority, priority should be part of Task - Task is managed by Notion or UI.
        self.task_memory = TaskMemory()
        self.logger.log("Starting new memory")
