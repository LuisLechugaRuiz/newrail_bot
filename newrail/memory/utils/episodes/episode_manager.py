from typing import Any, List, Optional, cast
import spacy
import subprocess
from spacy.util import get_package_path

from newrail.config.config import Config
from newrail.agent.behavior.execution import Execution
from newrail.memory.long_term_memory.weaviate import WeaviateMemory
from newrail.memory.utils.episodes.episode import Episode, Overview
from newrail.memory.utils.tokens_manager import TokensManager
from newrail.organization.utils.logger.agent_logger import AgentLogger
from newrail.parser.chat_parser import ChatParser
from newrail.utils.token_counter import count_string_tokens


# TODO: Compress episodes into meta-episode.
class EpisodeManager(object):
    def __init__(
        self,
        agent_id: str,
        team_id: str,
        logger: AgentLogger,
        current_goal: str = "",
        model: str = Config().fast_llm_model,
        tokens_percentage: float = Config().memory_goal_episodes_tokens_percentage,
    ):
        self.id = agent_id
        self.team_id = team_id
        self.long_term_memory = WeaviateMemory()
        self.logger = logger.create_logger("episode_manager")
        self.current_goal = current_goal
        self.last_episode = None
        self.episodes: List[Episode] = []
        self.max_token_threshold = TokensManager.calculate_max_tokens(
            model=model, tokens_percentage=tokens_percentage
        )
        self.model = model

    def add_episode(self, episode: Episode) -> None:
        """Add a new episode"""

        if self.last_episode:
            self.episodes.append(self.last_episode)
        self.last_episode = episode

    def clear_episodes(self) -> None:
        """Clear all the episodes"""

        self.episodes = []

    def create_episodes(
        self,
        execution: Execution,
        observation: str,
        should_summarize: bool = True,
    ) -> None:
        """Create a list of new episode based on the given operations"""

        max_content_tokens = round(self.max_token_threshold * 0.8)
        max_overview_tokens = round(self.max_token_threshold * 0.2)
        if should_summarize:
            episode_empty_prompt = Episode.get_summarized_episode_prompt(
                task_description=self.current_goal,
                action=execution.action,
                observation="",
                max_content_tokens=self.max_token_threshold,
                max_overview_tokens=self.max_token_threshold,
            )
            # Get as much text as possible. Leave the specific prompts for completion. TODO: Ensure that the model doesn't generate more than max_content_tokens.
            chunk_max_tokens = (
                self.get_model_tokens() - max_content_tokens - max_overview_tokens - 100
            )
        else:
            episode_empty_prompt = Overview.get_raw_episode_prompt(
                task_description=self.current_goal,
                action=execution.action,
                observation="",
                max_overview_tokens=self.max_token_threshold,
            )
            # Compress the text into chunks with the same max tokens than an episode.
            chunk_max_tokens = self.max_token_threshold

        full_text = execution.get_full_command() + f"\nObservation: {observation}"
        prefix = """This is the {n_episode} chunk of a sequence of {total_episodes} chunks while performing action: {action}\n"""
        chunks = self.preprocess_text(
            raw_prompt=episode_empty_prompt,
            text=full_text,
            chunk_max_tokens=chunk_max_tokens,
            prefix=prefix,
        )
        if len(chunks) == 0:
            return
        if len(chunks) == 1:
            self.create_episode(
                execution=execution,
                content=chunks[0],
                should_summarize=should_summarize,
            )
            return
        for idx, chunk in enumerate(chunks):
            prefix_formatted = prefix.format(
                n_episode=idx, total_episodes=len(chunks), action=execution.action
            )
            chunk = prefix_formatted + chunk
            self.create_episode(
                execution=execution,
                content=chunk,
                should_summarize=should_summarize,
            )

    def create_episode(
        self,
        execution: Execution,
        content: str,
        should_summarize: bool = False,
    ) -> Optional[Episode]:
        max_content_tokens = round(self.max_token_threshold * 0.8)
        max_overview_tokens = round(self.max_token_threshold * 0.2)
        if should_summarize:
            summarized_episode_prompt = Episode.get_summarized_episode_prompt(
                task_description=self.current_goal,
                action=execution.action,
                observation=content,
                max_content_tokens=max_content_tokens,
                max_overview_tokens=max_overview_tokens,
            )
            self.logger.log(
                f"Creating episode from summarized observation using prompt: {summarized_episode_prompt}"
            )
            parsed_response = ChatParser(logger=self.logger).get_parsed_response(
                system=summarized_episode_prompt,
                user="Remember to answer using the output format to provide an Episode!",
                containers=[Episode],
                smart_llm=False,  # TODO: smart vs fast
            )
            episode = parsed_response[0]
            if not episode:
                episode = Episode(
                    content=content,
                    overview=f"Executed action: {execution.action}",
                )  # Save raw data.
            else:
                episode = cast(Episode, episode)
        else:
            raw_episode_prompt = Overview.get_raw_episode_prompt(
                task_description=self.current_goal,
                action=execution.action,
                observation=content,
                max_overview_tokens=max_overview_tokens,
            )
            parsed_response = ChatParser(logger=self.logger).get_parsed_response(
                system=raw_episode_prompt,
                user="Remember to answer using the output format to provide an Overview!",
                containers=[Overview],
                smart_llm=False,  # TODO: smart vs fast
            )
            self.logger.log(
                f"Creating episode from raw observation using prompt: {raw_episode_prompt}"
            )
            overview = parsed_response[0]
            if overview:
                overview = cast(Overview, overview)
                episode = Episode(
                    content=content,
                    overview=overview.overview,
                )
            else:
                episode = Episode(
                    content=content,
                    overview=f"Executed action: {execution.action}",
                )  # Save raw data.
        episode.set_tool(capability=execution.get_capability(), action=execution.action)
        episode.set_order(order=len(self.episodes))
        self.save_episode(episode=episode)
        self.add_episode(episode=episode)
        return episode

    def create_meta_episode(
        self,
        question: Optional[str] = None,
    ) -> Optional[Episode]:
        """Create and save a new meta episode based on the given episodes"""

        if self.last_episode:
            self.episodes.append(self.last_episode)
            self.last_episode = None
        if len(self.episodes) == 0:
            raise Exception("No episodes to create a meta episode.")
        if len(self.episodes) == 1:
            return self.episodes[0]

        raw_prompt = self.get_meta_episode_prompt(
            new_content="", previous_content="", question=question
        )
        raw_prompt_tokens = count_string_tokens(string=raw_prompt)
        chunk_max_tokens = self.get_model_tokens()
        current_chunk = ""
        meta_episode = None
        i = 0
        num_episodes = len(self.episodes)
        for idx, episode in enumerate(self.episodes):
            future_chunk = current_chunk + episode.get_description()
            if (
                count_string_tokens(string=future_chunk) >= chunk_max_tokens
                or idx == num_episodes - 1
            ):
                # TODO: Make this better.
                if idx == num_episodes - 1:
                    current_chunk = future_chunk
                self.logger.log(f"Creating meta episode {i}", should_print=True)
                if meta_episode:
                    meta_episode_str = meta_episode.get_description()
                else:
                    meta_episode_str = ""
                prompt = self.get_meta_episode_prompt(
                    new_content=current_chunk,
                    previous_content=meta_episode_str,
                    question=question,
                )
                parsed_response = ChatParser(logger=self.logger).get_parsed_response(
                    system=prompt,
                    user="Remember to answer using the output format to provide an Episode!",
                    containers=[Episode],
                    smart_llm=False,  # TODO: smart vs fast
                )
                new_episode = parsed_response[0]
                if new_episode:
                    meta_episode = new_episode
                else:
                    meta_episode = Episode(
                        content=current_chunk,
                        overview=f"New summary integrating multiples episodes on {episode.overview}, failed to parse.",
                    )  # Save raw data.
                # Update raw_prompt_tokens to do not exceed the chunk_max_tokens
                raw_prompt = self.get_meta_episode_prompt(
                    new_content="",
                    previous_content=meta_episode.get_description(),
                    question=question,
                )
                raw_prompt_tokens = (
                    count_string_tokens(string=raw_prompt) + 100
                )  # Some extra tokens just in case.
                chunk_max_tokens = self.get_model_tokens() - raw_prompt_tokens
                current_chunk = ""
                i = i + 1
            else:
                current_chunk = future_chunk
        episodes_uuid = []
        for episode in self.episodes:
            episode_uuid = episode.get_uuid()
            if episode_uuid:
                episodes_uuid.append(episode_uuid)
        if meta_episode:
            self.save_episode(
                episode=meta_episode,
                child_episodes_uuid=episodes_uuid,
            )
            meta_episode.set_order(order=0)
            meta_episode.add_child_episodes(episodes=self.episodes)
            return meta_episode
        return None

    def clear(self) -> None:
        """Clear current episodes"""

        self.episodes = []

    def get_current_goal(self) -> str:
        """Get current goal"""

        return self.current_goal

    def get_episodes(self) -> List[Episode]:
        """Get episodes"""

        return self.episodes

    def get_episodes_str(self) -> str:
        """Get the current summary"""

        return "\n".join([episode.get_description() for episode in self.episodes])

    def get_last_episode(self) -> Optional[Episode]:
        """Get the last episode"""

        return self.last_episode

    def get_meta_episode_prompt(
        self, new_content: str, previous_content: str, question: Optional[str] = None
    ) -> str:
        """Get the meta episode prompt"""

        if question:
            return Episode.get_guided_meta_episode_prompt(
                task_description=self.current_goal,
                episodes=new_content,
                question=question,
                previous_content=previous_content,
                max_tokens=self.max_token_threshold,
            )
        return Episode.get_meta_episode_prompt(
            task_description=self.current_goal,
            episodes=new_content,
            previous_content=previous_content,
            max_tokens=self.max_token_threshold,
        )

    def get_model_tokens(self) -> int:
        """Get the tokens count of the model"""

        if self.model == Config().fast_llm_model:
            return Config().fast_token_limit
        else:
            return Config().smart_token_limit

    def get_tokens_count(self, episodes_str) -> int:
        """Get the tokens count of the summaries"""

        return count_string_tokens(episodes_str)

    def to_dict(self) -> dict[str, Any]:
        """Buffer to dict"""

        return {
            "agent_id": self.id,
            "team_id": self.team_id,
            "model": self.model,
            "current_goal": self.current_goal,
            "last_episode": self.last_episode.to_dict() if self.last_episode else None,
            "episodes": [episode.to_dict() for episode in self.episodes],
        }

    def set_current_goal(self, current_goal: str) -> None:
        """Update current task"""

        self.current_goal = current_goal

    @classmethod
    def from_dict(cls, data, logger):
        episode_manager = cls(
            agent_id=data["agent_id"],
            team_id=data["team_id"],
            logger=logger,
            model=data["model"],
            current_goal=data["current_goal"],
        )
        if data["last_episode"]:
            episode_manager.last_episode = Episode.from_dict(data=data["last_episode"])
        for episode_data in data["episodes"]:
            episode = Episode.from_dict(data=episode_data)
            episode_manager.episodes.append(episode)
        return episode_manager

    def save_episode(
        self,
        episode: Episode,
        child_episodes_uuid: List[str] = [],
    ) -> None:
        """Add episode to long term memory"""

        self.logger.log(f"Adding episode: {episode.get_description()}")
        episode_uuid = self.long_term_memory.store_episode(
            agent_uuid=self.id,
            team_uuid=self.team_id,
            overview=episode.overview,
            content=episode.content,
            capability=episode._capability,
            action=episode._action,
            created_at=episode._creation_time,
            child_episodes_uuid=child_episodes_uuid,
        )
        episode.link_to_uuid(uuid=episode_uuid)

    def preprocess_text(
        self,
        raw_prompt: str,
        text: str,
        chunk_max_tokens: int,
        prefix: Optional[str] = None,
    ) -> List[str]:
        """Preprocess text"""

        model_name = Config().browse_spacy_language_model
        try:
            model_path = get_package_path(model_name)
        except Exception:
            model_path = None

        if model_path is None:
            # Install the model if it's not available
            print(f"{model_name} is not installed. Installing now...")
            subprocess.check_call(["python", "-m", "spacy", "download", model_name])
        try:
            nlp = spacy.load(model_name)
        except Exception:
            raise Exception(f"Failed to load the spacy model: {model_name}")
        nlp.add_pipe("sentencizer")
        doc = nlp(text)
        sentences = [sent.text for sent in doc.sents]

        sentences_length = 0
        for sentence in sentences:
            sentences_length += count_string_tokens(sentence)
        self.logger.log(f"Total tokens: {sentences_length}")
        prompt_tokens = count_string_tokens(string=raw_prompt, model_name=self.model)
        if prefix:
            prompt_tokens = prompt_tokens + count_string_tokens(
                string=prefix, model_name=self.model
            )
        chunk_max_tokens = chunk_max_tokens - prompt_tokens

        chunks = [sentences.pop(0)]
        for sentence in sentences:
            # Accumulate on current chunk until max tokens is reached.
            future_chunk = chunks[-1] + " " + sentence
            if count_string_tokens(string=future_chunk) >= chunk_max_tokens:
                overlap_text = self.get_tokens(
                    text=chunks[-1], max_tokens=Config().episodes_overlap_tokens
                )
                chunks.append(overlap_text + " " + sentence)
            else:
                chunks[-1] = future_chunk
        self.logger.log(f"Number of chunks: {len(chunks)}")
        return chunks

    def get_tokens(self, text: str, max_tokens: int):
        """Get words from text"""
        words = text.split()
        tokens = ""
        for word in words:
            future_tokens = tokens + word + " "
            if count_string_tokens(string=future_tokens) >= max_tokens:
                return tokens.strip()
            tokens = future_tokens
        return tokens.strip()
