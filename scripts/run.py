#!/usr/bin/env python3

import select
import time
import threading
import warnings
from datetime import datetime
from typing import Callable, Optional

from newrail.config.config import Config
from newrail.config.configurator import Configurator
from newrail.agent.communication.database_handler.supabase_handler import (
    SupabaseHandler,
)

# TEMPORAL UNTIL WE CAN RECEIVE INFO ON REAL TIME FROM SUPA.
from newrail.utils.chat.communication.network_protocol import NetworkProtocol
from newrail.organization.requests.user_requests import (
    MaxIterationsRequest,
    ChatRequest,
    UpdateProtagonist,
    UserRequest,
)


warnings.filterwarnings("ignore", category=ResourceWarning)

DEF_SLEEP_INTERVAL = 0.2


class MessageListenerThread(threading.Thread):
    def __init__(self, network_protocol, received_callback: Optional[Callable] = None):
        super().__init__()
        self.network_protocol = network_protocol
        self.running = True
        self.received_callback = received_callback

    def run(self):
        while self.running:
            rlist, _, _ = select.select([self.network_protocol.sock], [], [], 1)
            if self.network_protocol.sock in rlist:
                message = self.network_protocol.receive()
                if self.received_callback:
                    self.received_callback(message)

    def stop(self):
        self.running = False


class NewRail:
    def __init__(self):
        self.global_cfg = Config()
        self.configurator = Configurator()
        self.network_protocol = NetworkProtocol(
            port=Config().org_network_port
        )  # TEMPORAL UNTIL WE CAN RECEIVE INFO ON REAL TIME FROM SUPA.
        self.organization = self.configurator.setup()
        self.database_handler = SupabaseHandler()

    def send_message(self, request: ChatRequest):
        print("Sending message to: ", request.agent_name)
        agent = self.database_handler.get_agent(
            organization_id=Config().organization_id,
            agent_name=request.agent_name,
        )
        if len(agent) == 0:
            print("Agent not found.")
            return
        if len(agent) > 1:
            print("More than one agent found.")
            return
        agent = agent[0]
        message_data = {
            "user_id": Config().user_id,
            "message": request.message,
        }
        data = {
            "agent_id": agent["id"],
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "data": message_data,
            "request_type": "message_from_user",
            "organization_id": Config().organization_id,
            "team_id": agent["team_id"],
        }
        self.database_handler.send_event(**data)

    def process_received_message(self, request: UserRequest):
        print("Received message: ", request)
        if not self.organization:
            raise Exception("Organization doesn't exists!")
        if isinstance(request, ChatRequest):
            self.send_message(request=request)
        if isinstance(request, MaxIterationsRequest):
            self.iterations = request.iterations
        elif isinstance(request, UpdateProtagonist):
            self.organization.update_protagonist(request.agent_name)

    def run(self):
        self.running = True

        if not self.organization:
            print("Failed to setup organization.")
            return

        # TEMPORAL UNTIL WE CAN RECEIVE INFO ON REAL TIME FROM SUPA.
        listener_thread = MessageListenerThread(
            self.network_protocol, self.process_received_message
        )
        listener_thread.start()

        try:
            while self.running:
                if not self.global_cfg.autonomous_mode:
                    if not self.organization.is_running():
                        team_invocations = self.configurator.get_team_invocations()
                        if team_invocations:
                            team_invocations_id = team_invocations["id"]
                            self.configurator.update_team_invocations(
                                team_invocations_id=team_invocations_id,
                                status="RUNNING",
                            )
                            self.organization.run(
                                max_iterations=team_invocations["num_iterations"],
                            )
                            self.configurator.delete_team_invocations(
                                team_invocations_id=team_invocations_id
                            )
                time.sleep(DEF_SLEEP_INTERVAL)
        except KeyboardInterrupt:
            print("\nCaught Ctrl+C, stopping NewRail...")
            self.stop()

    def stop(self):
        self.running = False


def main():
    newrail = NewRail()
    newrail.run()
    newrail.stop()


if __name__ == "__main__":
    main()
