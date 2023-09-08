#!/usr/bin/env python

import os
import select
import time
import threading
from typing import Callable, Optional

from newrail.config.config import Config
from newrail.utils.chat.communication.network_protocol import NetworkProtocol
from newrail.organization.requests.user_requests import (
    ChatRequest,
    MaxIterationsRequest,
    UpdateProtagonist,
    UserRequest,
)


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


class UserComm:
    def __init__(self):
        self.network_protocol = NetworkProtocol(Config().user_network_port)
        self.running = True
        self.user_folder = os.path.join(Config().permanent_storage, "user")

    def print_received_message(self, message):
        print(f"\nReceived message from executive_director: {message}\n")

    def run(self):
        listener_thread = MessageListenerThread(
            self.network_protocol, self.print_received_message
        )
        listener_thread.start()

        while self.running:
            # Ask for user input
            enter = int(
                input(
                    "Press 0 to send new iterations, 1 to change agent or 2 to send a message to any of the agents:"
                )
            )
            if enter == 0:
                iterations = input("Select number of iterations: ")
                self.send_request(MaxIterationsRequest(iterations=int(iterations)))
            if enter == 1:
                agent = input("Select agent:")
                self.send_request(UpdateProtagonist(agent_name=agent))
            elif enter == 2:
                agent = input(f"Select agent: ")
                if agent:
                    message = input("Enter message: ")
                    self.send_request(ChatRequest(agent_name=agent, message=message))
                else:
                    print("No agent selected, try again")
            # Sleep for a short duration to avoid busy waiting
            time.sleep(0.1)
        self.network_protocol.stop()

    def send_request(self, request: UserRequest):
        self.network_protocol.send(request, Config().org_network_port)
        print()

    def stop(self):
        self.running = False


def main():
    user_comm = UserComm()
    user_comm.run()
    user_comm.stop()


if __name__ == "__main__":
    main()
