from typing import Any, Dict, Optional
from queue import Queue

from newrail.agent.communication.broker.broker import Broker
from newrail.agent.config.config import AgentConfig
from newrail.agent.config.status import Status
from newrail.agent.communication.events.event import Event
from newrail.memory.utils.task.task import Task


class EventManager(object):
    def __init__(
        self,
        agent_config: AgentConfig,
        broker: Broker,
        supervisor_name: Optional[str],
    ):
        self.agent_config = agent_config
        self.broker = broker
        self.supervisor_name = supervisor_name
        self.received_events: Queue[Event] = Queue()
        self.received_tasks: Queue[Task] = Queue()
        # Connect to channel agent_incoming_events to get the events for the agent.
        self.subscribe_to_channels()

    def add_event(self, event_type: str, event_content: str) -> None:
        event = Event(type=event_type, content=event_content)
        self.received_events.put(event)

    def add_task(self, id: str, title: str, description: str, status: str) -> None:
        self.received_tasks.put(
            Task(
                id=id,
                title=title,
                description=description,
                status=status,
            )
        )

    def get_supervisor_name(self) -> Optional[str]:
        """Return supervisor name"""

        return self.agent_config.supervisor_name

    def get_event(self) -> Optional[Event]:
        """Get last stored event, if any"""

        if self.received_events.empty():
            return None

        return self.received_events.get()

    def get_task(self) -> Optional[Task]:
        if self.received_tasks.empty():
            return None
        return self.received_tasks.get()

    def receive_task(self, payload: Dict[str, Any]):
        data = payload["record"]
        if data["agent_id"] == self.agent_config.id:
            description = data["description"]
            if not description:
                description = ""
            self.add_task(
                id=data["id"],
                title=data["title"],
                description=description,
                status=data["status"],
            )

    def receive_message(self, payload: Dict[str, Any]):
        data = payload["record"]
        if data["agent_id"] == self.agent_config.id:
            if data["request_type"] == "message_from_agent":
                sender_name = self.broker.get_agent_info_from_id(
                    data["data"]["agent_id"]
                )["name"]
                message = data["data"]["message"]
                new_event = Event(
                    type="Message from agent received",
                    content=f"Agent name: {sender_name}. Message: {message}",
                )
                self.received_events.put(new_event)
            # TODO: Finish the implementation when adding user table.
            elif data["request_type"] == "message_from_user":
                # TODO: Enable this when user table is added.
                # user_email = self.broker.get_user_info_from_id(
                #    data["data"]["user_id"]
                # )["email"]
                fake_user_email = "newrail_leader@email.com"
                message = data["data"]["message"]
                new_event = Event(
                    type="Message from user received",
                    content=f"User with email: {fake_user_email}. Message: {message}",
                )
                self.received_events.put(new_event)

    def subscribe_to_channels(self):
        self.broker.subscribe_to_channel(
            schema="public",
            table_name="agent_incoming_events",
            event_type="INSERT",
            callback=self.receive_message,
        )
        self.broker.subscribe_to_channel(
            schema="public",
            table_name="tasks",
            event_type="INSERT",
            callback=self.receive_task,
        )
        self.broker.start_realtime_listener()

    def wait_for_event(
        self,
        event: str,
    ) -> str:
        self.agent_config.set_status(Status.WAITING)
        return f"Waiting for event: {event}"
