from typing import Any, List, Optional

from newrail.memory.utils.episodes.episode import Episode
from newrail.memory.utils.episodes.episode_manager import EpisodeManager
from newrail.memory.utils.goals.goal import Goal
from newrail.config.config import Config
from newrail.organization.utils.logger.agent_logger import AgentLogger


class GoalMemory:
    def __init__(
        self,
        agent_id: str,
        team_id: str,
        logger: AgentLogger,
        max_iterations=Config().max_goal_iterations,
    ):
        self.agent_id = agent_id
        self.team_id = team_id
        self.goals: List[Goal] = []
        self.evaluation = "No evaluation yet."
        self.episode_manager = EpisodeManager(
            agent_id=agent_id,
            team_id=team_id,
            logger=logger,
            tokens_percentage=Config().memory_goal_episodes_tokens_percentage,
        )
        self.max_iterations = max_iterations
        self.iterations = 0

    def add_episode(self, episode: Episode) -> None:
        """Add episode to current episode"""

        self.episode_manager.add_episode(episode=episode)

    def create_meta_episode(self) -> Optional[Episode]:
        """Create a episode from the current episodes."""

        meta_episode = self.episode_manager.create_meta_episode()
        if meta_episode:
            self.episode_manager.clear()
            # TODO: Should we do this?
            self.episode_manager.add_episode(episode=meta_episode)
        return meta_episode

    def get_current_goal(self) -> Optional[Goal]:
        """Get the first not finished goal"""

        return self.goals[0] if self.goals else None

    def get_evaluation(self) -> str:
        """Get evaluation of current goal"""

        return self.evaluation

    def get_last_episode(self) -> Optional[Episode]:
        """Get last episode"""

        return self.episode_manager.get_last_episode()

    def get_goal_episodes(self) -> List[Episode]:
        """Get goal episodes"""

        return self.episode_manager.get_episodes()

    def get_goals(self) -> List[Goal]:
        """Get goals"""

        return self.goals

    def max_iterations_reached(self) -> bool:
        """Check if the maximum number of iterations has been reached."""

        self.iterations += 1
        return self.iterations > self.max_iterations

    def update_evaluation(self, evaluation: str) -> None:
        """Update evaluation of current goal"""

        self.evaluation = evaluation

    def set_goals(self, goals: List[Goal]) -> None:
        """Set goals"""

        self.goals = goals
        self.iterations = 0

    def on_goal_finished(self) -> None:
        self.goals.pop(0)

    def to_dict(self) -> dict[str, Any]:
        """Goal memory to dict"""

        return {
            "agent_id": self.agent_id,
            "team_id": self.team_id,
            "goals": [goal.to_dict() for goal in self.goals],
            "episode_manager": self.episode_manager.to_dict(),
            "max_iterations": self.max_iterations,
            "iterations": self.iterations,
        }

    @classmethod
    def from_dict(cls, data, logger):
        goal_memory = cls(
            agent_id=data["agent_id"],
            team_id=data["team_id"],
            logger=logger,
            max_iterations=data.get("max_iterations"),
        )
        goal_memory.evaluation = data.get("evaluation")
        for goal in data["goals"]:
            goal_memory.goals.append(Goal.from_dict(data=goal))
        goal_memory.episode_manager = EpisodeManager.from_dict(
            data=data["episode_manager"], logger=logger
        )
        goal_memory.iterations = data["iterations"]
        return goal_memory
