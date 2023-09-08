from colorama import Fore
from concurrent.futures import ThreadPoolExecutor
from threading import RLock, Thread
import time
from typing import List, Optional, Union, Tuple
import traceback

from newrail.agent.agent import Agent
from newrail.agent.config.status import Status
from newrail.organization.utils.logger.agent_logger import AgentLogger
from newrail.organization.utils.logger.org_logger import OrgLogger
from newrail.organization.utils.priorities import (
    AgentPriority,
)
from newrail.organization.utils.priority_queue import AgentPriorityQueue


SLEEP_INTERVAL = 0.1


class Orchestrator:
    """
    Orchestrator class manages the execution of multiple agents concurrently with optional
    dynamic evaluation for agent prioritization.
    """

    def __init__(
        self,
        logger: Union[AgentLogger, OrgLogger],
        max_concurrent_agents: int,
        time_scaling_factor: float = 0.1,
    ):
        """
        Initializes the Orchestrator with the given parameters.

        Args:
            logger (Union[AgentLogger, OrgLogger]): The logger to be used for logging.
            max_concurrent_agents (int): The maximum number of agents to be executed concurrently.
            time_scaling_factor (float): The time scaling factor to be used for dynamic evaluation.
        """

        self._agents_lock = RLock()
        self._active_agents_lock = RLock()
        self._iterations_count_lock = RLock()
        self.last_execution_times = {}

        self.main_thread = None
        self.agents: dict[str, Tuple[float, Agent]] = {}
        self.active_agents = set()
        self.queue = AgentPriorityQueue()
        self.queue.set_time_scaling_factor(time_scaling_factor)
        self.logger = logger
        self.max_concurrent_agents = max_concurrent_agents
        self.stop_flag = True
        self.iteration_count = 0
        self.waiting_agents: set[Agent] = set()
        self.waiting_agents_lock = RLock()
        self.waiting_agents_thread = None

    def add_agent(self, agent: Agent, base_priority: int = 1):
        """
        Adds a new agent to the orchestrator's queue of agents.

        Args:
            agent (Agent): The agent to be added.
            base_priority (int): The base priority of the agent.
        """

        with self._agents_lock:
            self.last_execution_times[agent.cfg.name] = time.time()
            self.agents[agent.cfg.name] = (base_priority, agent)
            self.logger.log(f"Agent added: {agent.cfg.name}")

    def add_agent_to_queue(self, agent: Agent):
        """Adds a new agent to the orchestrator's queue of agents."""

        with self._agents_lock:
            priority, agent = self.agents[agent.cfg.name]
            self.logger.log(
                f"Adding agent {agent.cfg.name} with status: {agent.cfg.get_status().name} to the queue"
            )
            self.queue.put(
                (agent.cfg.name, agent),
                priority,
                self.last_execution_times[agent.cfg.name],
            )

    def add_agent_to_waiting(self, agent: Agent):
        """Adds a new agent to the set of waiting agents.

        Args:
            agent (Agent): The agent to be added.
        """

        with self.waiting_agents_lock:
            self.waiting_agents.add(agent)

    def agent_execution_callback(self, agent: "Agent"):
        """
        Callback function to handle agent execution completion.

        Args:
            agent (Agent): The agent that completed execution.
        """

        with self._active_agents_lock:
            self.active_agents.remove(agent)
        with self._iterations_count_lock:
            self.iteration_count += 1
        self.last_execution_times[agent.cfg.name] = time.time()
        self.add_agent_to_queue(agent)
        self.logger.log(f"Agent execution completed: {agent.cfg.name}")

    def delete_agent(self, agent_name: str):
        """
        Delete the agent.

        Args:
            agent_name (str): The name of the agent to be deleted.
        """

        with self._agents_lock:
            if agent_name in self.agents:
                del self.agents[agent_name]

    def execute_agent(self, agent: Agent):
        """
        Executes the given agent in a separate thread using a thread pool.

        Args:
            agent (Agent): The agent to execute.
        """

        def run_agent():
            try:
                with self._active_agents_lock:
                    if agent not in self.active_agents:
                        self.active_agents.add(agent)
                agent.step()
            except KeyboardInterrupt:
                print("\nCaught Ctrl+C, stopping orchestator")
                self.stop_internal()
            except Exception as e:
                tb_str = traceback.format_exc()
                self.logger.log_error(
                    f"Error executing agent: {agent.cfg.name}. Error: {e}\n{tb_str}"
                )
            finally:
                self.agent_execution_callback(agent)

        self._thread_pool.submit(run_agent)

    def is_running(self) -> bool:
        """
        Returns True if the orchestrator is running.
        """

        return not self.stop_flag

    def new_iteration(
        self,
        agent: Agent,
        max_iterations: Optional[int] = None,
    ) -> bool:
        """Start a new iteration using the given agent.

        Args:
            agent (Agent): The agent to execute.
            max_iterations (Optional[int], optional): The maximum number of iterations to run. Defaults to None.

        Returns:
            bool: True if remaining iterations are available, False otherwise.
        """

        with self._iterations_count_lock:
            if max_iterations:
                remaining_iterations = max_iterations - 1 - self.iteration_count
                self.logger.log(
                    f"{Fore.CYAN}Remaining iterations: {remaining_iterations}",
                    should_print=True,
                )
                if remaining_iterations:
                    self.logger.log(f"Executing agent: {agent.cfg.name}")
                    self.execute_agent(agent=agent)
                    return True
                return False
            return True

    def run(self, max_iterations: Optional[int] = None):
        """
        Starts the Orchestrator by executing agents in the queue.

        This method blocks until the stop() method is called or until max_iterations is reached.

        Args:
            max_iterations (Optional[int], optional): The maximum number of iterations to run. Defaults to None.
        """

        while not self.stop_flag:
            if not self.queue.empty():
                with self._active_agents_lock:
                    if len(self.active_agents) < self.max_concurrent_agents:
                        if not self.start_new_agent(max_iterations=max_iterations):
                            break
            time.sleep(SLEEP_INTERVAL)
        self.stop_internal()

    def start_new_agent(self, max_iterations: Optional[int] = None):
        """Starts a new agent from the queue.

        Args:
            max_iterations (Optional[int], optional): The maximum number of iterations to run. Defaults to None.

        Returns:
            bool: True if remaining iterations are available, False otherwise.
        """

        _, next_agent = self.queue.get()
        if next_agent:
            if next_agent.cfg.get_status() == Status.WAITING:
                self.logger.log(
                    f"Agent {next_agent.cfg.name} is waiting for events to be updated."
                )
                self.add_agent_to_waiting(next_agent)
                return True
            next_agent.update()
            return self.new_iteration(agent=next_agent, max_iterations=max_iterations)
        return True

    def stop_internal(self) -> None:
        """
        Stops the Orchestrator's thread_pool.
        """

        try:
            self.stop_flag = True
            with self._iterations_count_lock:
                self.iteration_count = 0
            self.logger.log("Stopping orchestrator...", should_print=True)
            self._thread_pool.shutdown(wait=True)
        except Exception as e:
            self.logger.log_critical(f"Exception occurred: {e}", should_print=True)
        finally:
            self.logger.log("Orchestrator stopped")

    def stop(self) -> None:
        """
        Stops the Orchestrator and waits for all threads to complete.
        """

        self.logger.log("Orchestrator stopped")
        self.stop_internal()
        if self.main_thread:
            self.main_thread.join()
        if self.waiting_agents_thread:
            self.waiting_agents_thread.join()

    def start(self, max_iterations: Optional[int] = None) -> None:
        """
        Starts the Orchestrator in a new thread.

        Args:
            max_iterations: The maximum number of iterations to run.
        """

        self.logger.log("Orchestrator started")
        self._thread_pool = ThreadPoolExecutor(max_workers=self.max_concurrent_agents)
        self.stop_flag = False
        self.main_thread = Thread(target=self.run, args=(max_iterations,))
        self.main_thread.start()
        self.waiting_agents_thread = Thread(target=self.waiting_agents_updater)
        self.waiting_agents_thread.start()

    def update_priorities(self, evaluations: List[AgentPriority]):
        """
        Save new priority scores for agents.

        Args:
            evaluations (List[AgentPriority]): A list of agent priority evaluations.
        """

        with self._agents_lock:
            for evaluation in evaluations:
                self.logger.log(
                    f"Adding: {evaluation.name} with priority score: {evaluation.priority} to queue",
                )
                _, agent = self.agents[evaluation.name]
                self.agents[evaluation.name] = (evaluation.priority, agent)

            # Clear the queue
            self.queue.clear()

            # Reinsert the agents with their updated priorities
            for agent_name, (priority, agent) in self.agents.items():
                self.queue.put(
                    (agent_name, agent),
                    priority,
                    self.last_execution_times[agent.cfg.name],
                )

    def insert_agent(self, agent_name: str):
        """
        Entry point to add agents to the queue or to the waiting list.

        Args:
            agent_name: The name of the agent whose status is being updated.
            new_status: The new status for the agent.
        """

        with self._agents_lock:
            if agent_name in self.agents:
                _, agent = self.agents[agent_name]
                agent_status = agent.cfg.get_status()
                if agent_status == Status.ACTIVE:
                    self.add_agent_to_queue(agent)
                elif agent_status == Status.WAITING:
                    self.add_agent_to_waiting(agent)

    def waiting_agents_updater(self):
        """Updates the status of waiting agents and adds them to the queue if they are ready to run."""

        while not self.stop_flag:
            with self.waiting_agents_lock:
                agents_to_activate: List[Agent] = []
                for agent in self.waiting_agents:
                    agent.update()
                    if agent.cfg.get_status() == Status.ACTIVE:
                        agents_to_activate.append(agent)
                for agent in agents_to_activate:
                    self.waiting_agents.remove(agent)
                    self.insert_agent(agent.cfg.name)
            time.sleep(SLEEP_INTERVAL)
