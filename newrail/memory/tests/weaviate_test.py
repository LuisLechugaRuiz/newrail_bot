import unittest
from newrail.config.config import Config
from newrail.memory.long_term_memory.weaviate import WeaviateMemory

cfg = Config()
cfg.debug_mode = True


class TestWeaviateMemory(unittest.TestCase):
    def setUp(self):
        self.weaviate = WeaviateMemory(
            restart=True
        )  # Careful!! This will delete all data in Weaviate...

    def test_similarity_store_and_retrieval(self):
        store_data_list = [
            {
                "topic": "Football",
                "content": "Football is a great sport.",
                "agent_name": "FootballAgent",
            },
            {
                "topic": "Basketball",
                "content": "The basketball team scored a three-pointer.",
                "agent_name": "BasketballAgent",
            },
            {
                "topic": "Tennis",
                "content": "The tennis player did amazing!",
                "agent_name": "TennisAgent",
            },
        ]
        for store_data in store_data_list:
            agent_uuid = self.weaviate.create_agent(store_data["agent_name"])
            self.weaviate.store_episode(
                agent_uuid=agent_uuid,
                topic=store_data["topic"],
                content=store_data["content"],
            )

        search_data_list = [
            {
                "topic": "Sports",
                "query": "Which sport is the best?",
                "expected_result": "Football is a great sport.",
            },
            {
                "topic": "Sports",
                "query": "What was the basketball score?",
                "expected_result": "The basketball team scored a three-pointer.",
            },
            {
                "topic": "Sports",
                "query": "How did the tennis player perform?",
                "expected_result": "The tennis player did amazing!",
            },
        ]

        for search_data in search_data_list:
            result = self.weaviate.search(
                topic=search_data["topic"], query=search_data["query"]
            )
            self.assertIsNotNone(result)
            if result:
                print("result:", result["content"])
                print("id:", result["_additional"]["id"])
                print("expected_result:", search_data["expected_result"])
                self.assertEqual(result["content"], search_data["expected_result"])

        fake_question = {
            "topic": "Science",
            "query": "When will we create newrail?",
            "expected_result": "This year.",
        }
        result = self.weaviate.search(
            topic=fake_question["topic"], query=fake_question["query"]
        )
        self.assertIsNone(result)

    def test_meta_episodes(self):
        goal_episode = {
            "topic": "Goal",
            "content": "Messi scored a beautiful goal on the last minute.",
        }
        shoes_episode = {
            "topic": "Shoes",
            "content": "Adidas are the best shoes for football.",
        }
        episodes_uuid = []
        football_agent_uuid = self.weaviate.create_agent("TestFootballAgent")
        goal_episode_uuid = self.weaviate.store_episode(
            agent_uuid=football_agent_uuid,
            topic=goal_episode["topic"],
            content=goal_episode["content"],
        )
        episodes_uuid.append(goal_episode_uuid)
        shoes_episode = self.weaviate.store_episode(
            agent_uuid=football_agent_uuid,
            topic=shoes_episode["topic"],
            content=shoes_episode["content"],
        )
        meta_episode = {
            "topic": "Football",
            "content": "Argentina won the game.",
        }
        self.weaviate.store_episode(
            agent_uuid=football_agent_uuid,
            topic=meta_episode["topic"],
            content=meta_episode["content"],
            child_episodes_uuid=episodes_uuid,
        )
        query = {
            "topic": "Sport",
            "query": "How was the game?",
        }

        result = self.weaviate.recursive_search(
            topic=query["topic"], query=query["query"], depth=1
        )
        self.assertEqual(result[0], meta_episode["content"])
        self.assertEqual(result[1], goal_episode["content"])


if __name__ == "__main__":
    unittest.main()
