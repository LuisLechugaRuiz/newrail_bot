from newrail.agent.config.config import AgentConfig
from newrail.agent.config.status import Status
from newrail.agent.behavior.task_manager import TaskManager
from newrail.agent.communication.broker.broker import Broker
from newrail.agent.communication.events.event import Event
from newrail.agent.communication.events.event_manager import EventManager
from newrail.agent.communication.requests.request_manager import RequestManager
from newrail.config.config import Config
from newrail.memory.long_term_memory.weaviate import WeaviateMemory
from newrail.memory.short_term_memory.episodic_memory import EpisodicMemory
from newrail.memory.utils.task.task import Task
from newrail.organization.utils.logger.agent_logger import AgentLogger


class Agent:
    def __init__(
        self,
        agent_config: AgentConfig,
    ):
        self.cfg = agent_config
        self.global_cfg = Config()
        self.logger = AgentLogger(
            agent_name=self.cfg.name,
            agent_config=self.cfg,
            agent_folder=self.cfg.folder,
            process_name="main",
        )
        self.long_term_memory = WeaviateMemory()
        self.short_term_memory = EpisodicMemory(
            agent_id=self.cfg.id,
            team_id=self.cfg.team_id,
            folder=self.cfg.folder,
            logger=self.logger,
        )
        self.broker = Broker(agent_config=self.cfg, agent_logger=self.logger)
        self.event_manager = EventManager(
            agent_config=self.cfg,
            broker=self.broker,
            supervisor_name=self.cfg.supervisor_name,
        )
        self.request_manager = RequestManager(agent_config=self.cfg, broker=self.broker)
        self.task_manager = TaskManager(
            agent_config=self.cfg,
            agent_name=self.cfg.name,
            agent_logger=self.logger,
            event_manager=self.event_manager,
            request_manager=self.request_manager,
            memory=self.short_term_memory,
        )

    def add_event(self, event: Event):
        self.task_manager.add_event(event=event)

    def add_task(self, task: Task):
        self.task_manager.add_task(task=task)

    # TODO: Implement as needed to ensure clean-up after agent is deleted.
    def delete(self):
        """Called by org if the agent should be deleted."""

        self.cfg.remove()
        return True

    def step(self):
        self.task_manager.step()  # Main flow of the agent at one iteration.
        self.cfg.save()  # Update the config file.

    def update(self) -> None:
        """Update agent events and tasks."""

        event = self.event_manager.get_event()
        if event:
            self.add_event(event=event)
        task = self.event_manager.get_task()
        if task:
            self.add_task(task=task)

    def update_status(self, status: Status):
        """Update the status of the agent."""

        self.task_manager.update_status(status=status)
