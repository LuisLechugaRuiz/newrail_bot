import random
import os
import unittest
import time

from newrail.config.config import Config
from newrail.organization.utils.logger.agent_logger import AgentLogger
from newrail.organization.utils.orchestrator import Orchestrator
from newrail.organization.utils.priority_queue import AgentPriorityQueue


class TestableOrchestrator(Orchestrator):
    @property
    def active_agents_count(self):
        return len(self.active_agents)

    @property
    def queue_empty(self):
        return self.queue.empty()

    def get_agents(self):
        return [tuple[1] for tuple in self.agents.values()]


class MockAgent:
    def __init__(self, name, with_exception=False):
        self.cfg = self.Config(name)
        self.with_exception = with_exception

    class Config:
        def __init__(self, name):
            self.name = name

    def step(self):
        if self.with_exception:
            raise Exception("This is a test exception")
        time.sleep(0.5)


class MockEvaluation:
    def __init__(self, agent_name, priority):
        self.name = agent_name
        self.priority = priority

    @classmethod
    def evaluate(cls, agents):
        evaluations = []
        for agent in agents:
            evaluations.append(MockEvaluation(agent.cfg.name, random.uniform(1, 5)))
        return evaluations


class TestOrchestrator(unittest.TestCase):
    def setUp(self):
        self.max_concurrent_agents = 3
        self.mocked_logger = AgentLogger("TestOrchestrator", os.getcwd())
        self.orchestrator = TestableOrchestrator(
            self.mocked_logger,
            self.max_concurrent_agents,
        )
        self.testing_agents = [MockAgent(f"Agent-{i}") for i in range(5)]
        for agent in self.testing_agents:
            self.orchestrator.add_agent(agent)

    def tearDown(self):
        self.orchestrator.stop()
        if not Config().debug_mode:
            self.mocked_logger.clear_logger()

    def test_add_delete_agent_while_running(self):
        self.mocked_logger.log("---Test add and remove agents while running---")
        self.orchestrator.start()
        time.sleep(1)
        new_agent = MockAgent("NewAgent")
        self.orchestrator.add_agent(new_agent)
        self.assertIn(new_agent, self.orchestrator.get_agents())
        self.orchestrator.delete_agent(new_agent.cfg.name)
        self.assertNotIn(new_agent, self.orchestrator.get_agents())
        self.orchestrator.stop()

    def test_agent_execution_with_exceptions(self):
        self.mocked_logger.log("---Test agent execution with exceptions---")
        faulty_agent = MockAgent("FaultyAgent", with_exception=True)
        self.orchestrator.add_agent(agent=faulty_agent)
        self.orchestrator.start()
        self.assertRaises(Exception)
        time.sleep(2)
        self.orchestrator.stop()

    def test_stop_before_agents_complete_execution(self):
        self.mocked_logger.log("---Test stop before agents complete execution---")
        self.orchestrator.start()
        time.sleep(2)
        self.orchestrator.stop()
        self.assertTrue(self.orchestrator.stop_flag)

    def test_max_iterations_reached(self):
        self.mocked_logger.log("---Test max iterations reached---")
        max_iterations = 1
        self.orchestrator.start(max_iterations=max_iterations)
        time.sleep(5)
        self.assertEqual(self.orchestrator.iteration_count, max_iterations)
        self.orchestrator.stop()

    def test_queue_never_empty(self):
        self.mocked_logger.log("---Test queue never empty---")
        self.orchestrator.start()
        start_time = time.time()
        while time.time() - start_time < 5:
            self.assertFalse(self.orchestrator.queue_empty)
            time.sleep(0.2)
        self.orchestrator.stop()


class TestAgentPriorityQueue(unittest.TestCase):
    def test_put_and_get(self):
        queue = AgentPriorityQueue()
        queue.put(("Agent-0", None), 3, time.time())
        queue.put(("Agent-1", None), 2, time.time())
        queue.put(("Agent-2", None), 1, time.time())
        queue.put(("Agent-3", None), 5, time.time())
        queue.put(("Agent-4", None), 4, time.time())
        expected_order = ["Agent-2", "Agent-1", "Agent-0", "Agent-4", "Agent-3"]
        actual_order = []
        while not queue.empty():
            agent_name, _ = queue.get()
            actual_order.append(agent_name)
        self.assertEqual(actual_order, expected_order)


if __name__ == "__main__":
    unittest.main()
