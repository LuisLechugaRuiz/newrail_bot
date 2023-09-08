import ast
from typing import Any, Dict, List, Tuple
import uuid

from newrail.agent.behavior.attention import Attention
from newrail.agent.behavior.plan import Plan
from newrail.agent.behavior.execution import Execution
from newrail.agent.communication.events.event import Event
from newrail.agent.communication.events.event_manager import EventManager
from newrail.agent.communication.requests.request_manager import RequestManager
from newrail.agent.config.stage import Stage
from newrail.agent.config.status import Status
from newrail.agent.config.config import AgentConfig
from newrail.capabilities.utils.builder import CapabilityBuilder
from newrail.capabilities.capability import Capability
from newrail.memory.utils.episodes.episode import Episode
from newrail.memory.utils.goals.goal_status import GoalStatus
from newrail.memory.utils.thought.thought import Thought
from newrail.memory.utils.task.task import Task
from newrail.memory.utils.task.task_status import TaskStatus
from newrail.memory.short_term_memory.episodic_memory import EpisodicMemory
from newrail.memory.long_term_memory.weaviate import WeaviateMemory
from newrail.organization.utils.logger.agent_logger import AgentLogger
from newrail.utils.storage import get_org_folder


class TaskManager:
    def __init__(
        self,
        agent_config: AgentConfig,
        agent_name: str,
        agent_logger: AgentLogger,
        event_manager: EventManager,
        request_manager: RequestManager,
        memory: EpisodicMemory,
    ):
        self.agent_config = agent_config
        self.name = agent_name
        self.event_manager = event_manager
        self.request_manager = request_manager
        self.logger = agent_logger.create_logger("task_manager")
        self.memory = memory
        self.long_term_memory = WeaviateMemory()
        self.capabilities: dict[str, "Capability"] = {}
        self.get_capabilities(self.agent_config.capabilities)
        self.task = None
        self.logger.log("Task Manager started.")

    def get_capabilities(self, capabilities: List[str]) -> None:
        for capability in capabilities:
            self.capabilities[capability] = CapabilityBuilder.get_capability(
                name=capability,
                agent_config=self.agent_config,
                event_manager=self.event_manager,
                request_manager=self.request_manager,
                org_folder=get_org_folder(self.agent_config.organization_name),
                agent_logger=self.logger,
            )

    def step(self):
        stage = self.agent_config.get_stage()
        self.logger.log(f"Starting: {stage.name}")
        if stage == Stage.PLANNING:
            self.plan_stage()
        elif stage == Stage.ATTENTION:
            self.attention_stage()
        elif stage == Stage.EXECUTION:
            self.execute_stage()
        # elif stage == Stage.INTEGRATION:
        #    self.integrate_stage()

    def add_event(self, event: Event):
        if not self.task:
            self.create_task(
                title="Handle event",
                description=f"Take the necessary actions to respond to the new event. Event type:{event.type}, content: {event.content}",
            )
        if self.agent_config.status == Status.WAITING:
            self.update_status(status=Status.ACTIVE)
        self.memory.add_event(event=event)

    def add_task(self, task: Task):
        self.memory.add_task(task=task)
        if self.agent_config.status == Status.WAITING:
            self.update_status(status=Status.ACTIVE)

    def create_task(self, title: str, description: str):
        id = str(uuid.uuid4())
        status = TaskStatus.IN_PROGRESS.value
        new_task = Task(
            id=id,
            title=title,
            description=description,
            status=status,
        )
        self.request_manager.create_task(
            id=id,
            title=title,
            description=description,
            status=status,
        )
        self.add_task(task=new_task)

    def get_capabilities_description(self) -> str:
        capabilities_high_level_description = ""
        for capability_name in self.capabilities.keys():
            try:
                capabilities_high_level_description += self.get_capability_description(
                    capability_name=capability_name, detailed=False
                )
            except Exception as e:
                error_msg = f"Error updating context using capability: {capability_name}, exception: {e}"
                self.logger.log(f"{error_msg}", should_print=True)
        return capabilities_high_level_description

    def execute_stage(self):
        """Execution stage, execute the action and move to validation"""

        goal = self.memory.get_current_goal()
        if not goal:
            raise Exception("No goal to execute")
        if goal.get_status() == GoalStatus.NOT_STARTED:
            goal.update_status(status=GoalStatus.IN_PROGRESS)
        capability_name = goal.capability
        capability = self.capabilities.get(capability_name)
        if not capability:
            error_msg = f"Capability {capability_name} is not supported by the agent, planning a new step"
            self.logger.log(error_msg)
            # TODO: Add a way to notify planning
            # self.memory.update_evaluation(evaluation=error_msg)
            self.update_stage(Stage.PLANNING)
            return
        try:
            action_description = self.get_action_description(
                capability_name=capability_name, action=goal.action
            )
        except Exception:
            error_msg = f"Action {goal.action} is not supported by the agent, planning a new step"
            self.logger.log(error_msg)
            # TODO: Add a way to notify planning
            # self.memory.update_evaluation(evaluation=error_msg)
            self.update_stage(Stage.PLANNING)
            return

        thought, execution = Execution.get_execution(
            agent_name=self.agent_config.name,
            task=self.task.get_description(),
            goal=goal.get_description(),
            previous_thought=self.memory.get_thought().get_description(),
            action_description=action_description,
            relevant_information=self.memory.get_relevant_information(),
            logger=self.logger,
        )
        if thought and execution:
            execution.set_capability(capability=capability_name)
            self.update_thought(thought=thought)
            success, observation = self.execute_action(
                execution=execution, capability=capability
            )
            if success:
                self.logger.log(f"Observation: {observation}", should_print=True)
            else:
                self.logger.log(
                    f"Observation with error: {observation}", should_print=True
                )
            try:
                episode = capability.get_episode(
                    execution=execution, observation=observation
                )
            except Exception as e:
                self.logger.log(
                    f"Error getting episode from capability, error: {e}",
                    should_print=True,
                )
                self.update_stage(Stage.PLANNING)
                return
            self.memory.add_goal_episode(episode=episode)
            self.update_stage(Stage.PLANNING)
            self.notify_stage_event(data=execution.dict())
        else:
            self.logger.log(
                "Couldn't parse action to execute, trying again..", should_print=True
            )

    def attention_stage(self):
        """Attention stage, gather information before execution"""

        goal = self.memory.get_current_goal()
        if not goal:
            raise Exception("No goal to execute")
        goal_episodes_str = "\n".join(
            [
                episode.get_overview(show_uuid=True)
                for episode in self.memory.get_goal_episodes()
            ]
        )
        iterate = True
        episode = None
        thought = self.memory.get_thought().get_description()
        relevant_information = self.memory.get_relevant_information()
        last_episode = self.memory.get_last_episode()
        if last_episode:
            last_episode_str = last_episode.get_description(include_child_episodes=True)
        else:
            last_episode_str = ""
        while iterate:
            iterate = False
            most_similar_episodes = self.memory.get_similar_episodes()
            most_similar_episodes_str = ""
            for question, answer in most_similar_episodes.items():
                most_similar_episodes_str += f"\nQuestion: {question}\nEpisode: {answer.get_description(include_child_episodes=True)}\n"
            if episode:
                attention = Attention.get_relevant_memory_iterative(
                    goal=goal.get_description(),
                    capability=goal.capability,
                    action=goal.action,
                    thought=thought,
                    remembered_episode=episode.get_description(),
                    most_similar_episodes=most_similar_episodes_str,
                    relevant_information=relevant_information,
                    logger=self.logger,
                )
            else:
                attention = Attention.get_relevant_memory(
                    goal=goal.get_description(),
                    capability=goal.capability,
                    action=goal.action,
                    thought=thought,
                    recent_episodes=goal_episodes_str,
                    most_recent_episode=last_episode_str,
                    most_similar_episodes=most_similar_episodes_str,
                    logger=self.logger,
                )

            if not attention:
                self.logger.log(
                    "Failed to get relevant information from attention, trying again..",
                    should_print=True,
                )
                continue
            # TODO: RETHINK THIS. IT DOESN'T WORK AS EXPECTED AS WE ONLY CALL IT IN CASE OF EPISODE.
            # if attention.search_query:
            # self.update_similar_episodes(queries=attention.search_query)
            if attention.remember_episode_uuid:
                episode = self.long_term_memory.get_episode(
                    agent_uuid=self.agent_config.id,
                    episode_uuid=attention.remember_episode_uuid,
                )
                iterate = True
            # TODO: Update to context.
            self.memory.update_relevant_information(
                relevant_information=attention.relevant_information
            )
        self.update_stage(Stage.EXECUTION)

    def plan_stage(self):
        self.task = self.memory.get_task()
        if not self.task:
            if self.agent_config.get_status() == Status.ACTIVE:
                self.logger.log("No task, waiting for new task..", should_print=True)
                self.agent_config.set_status(Status.WAITING)
            return

        if self.task.status == TaskStatus.NOT_STARTED:
            self.update_task(status=TaskStatus.IN_PROGRESS)

        goals = self.memory.get_goals()
        if len(goals) > 0:
            goals_str = "\n".join(
                goal.get_description() for goal in self.memory.get_goals()
            )
        else:
            goals_str = "No goals yet"
        events = self.memory.get_events()
        if events:
            events_str = "\n".join(str(event) for event in events)
        else:
            events_str = "No events."
        self.memory.clear_events()

        # TODO: DEFINE DIFFERENCE BETWEEN GOAL AND TASK EPISODES.
        task_episodes = self.memory.get_goal_episodes()
        task_episodes_str = "\n".join(
            episode.get_overview(show_uuid=True) for episode in task_episodes
        )
        last_episode = self.memory.get_last_episode()
        if last_episode:
            last_episode_str = last_episode.get_description()
        else:
            last_episode_str = ""
        # TODO: Optimize prompt.. due to max length we don't want to add too much info to plan.
        # 1. Consider removing relevant information from plan.
        # 2. Change summary.
        # 3. Remove evaluation.
        thought, plan = Plan.get_plan(
            agent_name=self.agent_config.name,
            agent_mission=self.agent_config.mission,
            task=self.task.get_description(),
            goals=goals_str,
            previous_thought=self.memory.get_thought().get_description(),
            summary=task_episodes_str,
            last_episode=last_episode_str,
            events=events_str,
            relevant_information=self.memory.get_relevant_information(),
            capabilities_description=self.get_capabilities_description(),
            logger=self.logger,
        )
        if thought and plan:
            self.update_thought(thought=thought)
            if plan.search_queries:
                self.update_similar_episodes(queries=plan.search_queries)
            # TODO: This needs validation before setting the goals !! LLM can allucinate and remove all the previous planned goals, we should have saveguards for this!!
            if plan.goals:
                if self.verify_action(
                    capability_name=plan.goals[0].capability,
                    action=plan.goals[0].action,
                ):
                    self.memory.set_goals(goals=plan.goals)
                    self.update_stage(Stage.ATTENTION)
                else:
                    thought = self.memory.get_thought()
                    thought.criticism += f"\n Capability: {plan.goals[0].capability} Action: {plan.goals[0].action} are not valid. Please verify that the action exists in the capability."
                    self.update_thought(thought=thought)
            else:
                # if plan.finished():
                # VERIFY PLAN HERE TO CHECK THAT WE ARE NOT MISSING ANYTHING
                self.report_finished(success=True)
        else:
            self.logger.log("Couldn't plan a goal, trying again..", should_print=True)

    def get_capability_description(
        self,
        capability_name: str,
        detailed: bool = False,
    ) -> str:
        capability = self.capabilities.get(capability_name)
        if capability is None:
            self.logger.log("Critical error! Wrong capability.")
            raise ValueError(f"Unknown capability: {capability_name}")

        capability_description = f"\n=== CAPABILITY: {capability_name} ===\n"
        capability_description += capability.info.get_capabilitiy_description(
            detailed=detailed
        )
        context = capability.info.get_context()
        if context:
            capability_description += f"\n=== CONTEXT ===\n{context}\n"
        return capability_description

    def get_action_description(
        self,
        capability_name: str,
        action: str,
    ) -> str:
        capability = self.capabilities.get(capability_name)
        if capability is None:
            self.logger.log("Critical error! Wrong capability.")
            raise ValueError(f"Unknown capability: {capability_name}")

        action_description = f"\n=== ACTION: {action} ===\n"
        action_description += capability.get_action_doc(action=action)

        # TODO: Rethink this.
        context = capability.info.get_context()
        if context:
            action_description += f"\n=== CONTEXT ===\n{context}\n"
        return action_description

    def update_similar_episodes(self, queries: List[str], num_relevant: int = 1):
        """Update the most similar episode to the query"""

        similar_episodes: Dict[str, Episode] = {}
        for query in queries:
            similar_episode = self.long_term_memory.search_episode(
                query=query, agent_uuid=self.agent_config.id, num_relevant=num_relevant
            )
            if similar_episode:
                similar_episodes[query] = similar_episode
        if similar_episodes:
            self.memory.update_similar_episodes(similar_episodes=similar_episodes)

    @classmethod
    def execute_action(
        cls,
        execution: "Execution",
        capability: Capability,
    ) -> Tuple[bool, str]:
        function_name = execution.action
        try:
            function = getattr(capability, function_name)
        except AttributeError as e:
            return (
                False,
                f"Action: {execution.action} doesn't exist on capability: {capability.name}. Error: {e}.",
            )
        try:
            evaluated_args = {
                key: cls.evaluate_literal(val)
                for key, val in execution.arguments.items()
            }
            return (True, function(**evaluated_args))
        except Exception as e:
            return (
                False,
                f"Incorrect arguments for action: {execution.action} on capability: {capability.name}. Error: {e}.\nThese are the instructions to use the action: {capability.get_action_doc(execution.action)}\nVerify the arguments and the format declared at Args.",
            )

    @classmethod
    def evaluate_literal(cls, value):
        try:
            return ast.literal_eval(value)
        except (ValueError, SyntaxError):
            return value

    def report_finished(
        self,
        success: bool,
    ):
        if not self.task:
            raise Exception("No task to report finished for.")
        task_description = self.task.get_description()
        if success:
            prefix_msg = "I achieved"
        else:
            prefix_msg = "I couldn't achieve"
        self.update_task(status=TaskStatus.DONE)
        # TODO: ENABLE THIS VERIFYING IF WE SHOULD NOTIFY TO OUR SUPERVISOR.
        # MAYBE IT SHOULD ALWAYS BE ENABLED, BUT FOR NOW DURING TESTING ONLY 1 AGENT IS DISABLED AS WE DON'T WANT TO WAKE UP SUPERVISOR DURNING TESTING.
        # message = f"{prefix_msg} my task {task_description}, as part of my mission {self.agent_config.mission}.\nThis is a summary: {self.memory.get_summary()}"
        # self.report_progress(message=message)

    def report_progress(self, message: str):
        """Report progress to supervisor."""

        if self.agent_config.supervisor_name:
            self.logger.log(f"Reporting progress to supervisor:\n {message}")
            self.logger.log(
                self.request_manager.send_message_to_agent(
                    agent_name=self.agent_config.supervisor_name, message=message
                )
            )
        else:
            self.logger.log("No supervisor to report progress to.")

    def update_stage(self, stage: Stage):
        """Update stage of the agent."""

        self.agent_config.set_stage(stage)
        self.request_manager.update_agent(self.agent_config)

    def update_status(self, status: Status):
        """Update status of the agent."""

        self.agent_config.set_status(status)
        self.request_manager.update_agent(self.agent_config)

    def update_thought(self, thought: Thought):
        """Update the current thought."""

        self.request_manager.send_notification(
            event_type="THOUGHT", data=thought.to_dict()
        )
        self.memory.update_thought(thought)

    def update_task(self, status: TaskStatus):
        """Update the current task."""

        if not self.task:
            raise ValueError("No task to update.")
        self.request_manager.update_task(task_id=self.task.id, status=status.value)

        if status == TaskStatus.DONE:
            self.memory.set_task_finished()
            self.task = self.memory.get_task()

    def notify_stage_event(self, data: Any):
        """Notify the event of the current stage."""

        stage = self.agent_config.get_stage()
        self.request_manager.send_notification(event_type=stage.name, data=data)

    def verify_action(self, capability_name: str, action: str):
        capability = self.capabilities.get(capability_name)
        if not capability:
            return False
        try:
            self.get_action_description(capability_name=capability_name, action=action)
            return True
        except Exception:
            return False
