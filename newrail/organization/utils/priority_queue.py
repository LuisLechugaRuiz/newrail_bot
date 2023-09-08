import heapq
import math
import threading
import time
from typing import Optional, Tuple

from newrail.agent.agent import Agent


class AgentPriorityQueue:
    def __init__(self):
        self.queue = []
        self.lock = threading.RLock()
        self.time_scaling_factor = 1
        self.reference_time = time.time()

    def put(self, item, base_priority, last_execution_time, reference_time=None):
        with self.lock:
            agent_name, agent = item
            if reference_time is None:
                reference_time = self.reference_time
            elapsed_time = reference_time - last_execution_time
            priority = base_priority * math.exp(
                -self.time_scaling_factor * elapsed_time
            )
            heapq.heappush(self.queue, (priority, agent_name, agent))

    def get(self) -> Tuple[str, Agent]:
        with self.lock:
            _, agent_name, agent = heapq.heappop(self.queue)
            return agent_name, agent

    def empty(self):
        with self.lock:
            return len(self.queue) == 0

    def qsize(self):
        with self.lock:
            return len(self.queue)

    def clear(self):
        with self.lock:
            while not self.empty():
                self.get()

    def front(self) -> Optional[Tuple[float, Agent]]:
        with self.lock:
            if not self.empty():
                priority, _, agent = self.queue[0]
                return priority, agent
            return None

    def back(self) -> Optional[Tuple[float, Agent]]:
        with self.lock:
            if not self.empty():
                priority, _, agent = max(self.queue, key=lambda x: (x[0], x[1]))
                return priority, agent
            return None

    def set_time_scaling_factor(self, k):
        self.time_scaling_factor = k
