from typing import List, Optional
import weaviate

from newrail.memory.utils.episodes.episode import Episode
from newrail.memory.utils.embeddings import get_ada_embedding
from newrail.config.config import Config
from weaviate.exceptions import (
    ObjectAlreadyExistsException,
)


DEF_SCHEMA = {
    "classes": [
        {
            "class": "Agent",
            "description": "Agent",
            "properties": [
                {
                    "name": "name",
                    "dataType": ["text"],
                    "description": "The agent name",
                },
            ],
        },
        {
            "class": "Team",
            "description": "Team",
            "properties": [
                {
                    "name": "name",
                    "dataType": ["text"],
                    "description": "The team name",
                },
            ],
        },
        {
            "class": "Episode",
            "description": "Episode",
            "properties": [
                {
                    "name": "meta_episode",
                    "dataType": ["Episode"],
                    "description": "The episode which generalizes this episode",
                },
                {
                    "name": "overview",
                    "dataType": ["text"],
                    "description": "The overview of the episode",
                },
                {
                    "name": "content",
                    "dataType": ["text"],
                    "description": "Content of the information",
                },
                {
                    "name": "capability",
                    "dataType": ["text"],
                    "description": "The capability that was used in the episode",
                },
                {
                    "name": "action",
                    "dataType": ["text"],
                    "description": "The action that was performed in the episode",
                },
                {
                    "name": "child_episodes_uuid",
                    "dataType": ["text[]"],
                    "description": "The uuids of the child episodes",
                },
                {
                    "name": "agent",
                    "dataType": ["Agent"],
                    "description": "The agent that experienced the episode",
                },
                {
                    "name": "team",
                    "dataType": ["Team"],
                    "description": "The team of the agent that experienced the episode",
                },
                {
                    "name": "created_at",
                    "dataType": ["text"],
                    "description": "The date the episode was created",
                },
            ],
        },
    ]
}


class WeaviateMemory(object):
    def __init__(self):
        weaviate_key = Config().weaviate_key
        if weaviate_key:
            # Run on weaviate cloud service
            auth = weaviate.auth.AuthApiKey(api_key=weaviate_key)
            self.client = weaviate.Client(
                url=Config().weaviate_url,
                auth_client_secret=auth,
                additional_headers={
                    "X-OpenAI-Api-Key": Config().openai_api_key,
                },
            )
        else:
            # Run locally"
            self.client = weaviate.Client(
                url=f"{Config().local_weaviate_url}:{Config().weaviate_port}"
            )
        # self.client.schema.delete_all()
        self._create_schema()

    def _create_schema(self):
        # Create classes in Weaviate
        if not self.client.schema.contains(DEF_SCHEMA):
            self.client.schema.create(DEF_SCHEMA)

    def create_agent(self, agent_name: str, agent_id: str) -> Optional[str]:
        try:
            agent_uuid = self.client.data_object.create(
                data_object={"name": agent_name},
                class_name="Agent",
                uuid=agent_id,
            )
            if agent_uuid != agent_id:
                raise Exception(
                    "Agent uuid is not the same as the one provided."
                )  # TODO: Verify that this never triggers.
            if Config().debug_mode:
                print("Added new agent:", agent_name, "with uuid:", agent_uuid)
            return agent_uuid
        except ObjectAlreadyExistsException as err:
            print("Agent already exists on long term memory:", err)

    def create_team(self, team_name: str, team_id: str) -> Optional[str]:
        try:
            team_uuid = self.client.data_object.create(
                data_object={"name": team_name},
                class_name="Team",
                uuid=team_id,
            )
            if team_uuid != team_id:
                raise Exception(
                    "Agent uuid is not the same as the one provided."
                )  # TODO: Verify that this never triggers.
            if Config().debug_mode:
                print("Added new team:", team_name, "with uuid:", team_uuid)
            return team_uuid
        except ObjectAlreadyExistsException as err:
            print("Team already exists on long term memory:", err)

    def _get_overview_filter(self, overview):
        filter_obj = {
            "path": ["overview", "overview", "name"],
            "operator": "Equal",
            "valueText": overview,
        }
        return filter_obj

    def _get_relevant(
        self,
        vector,
        class_name,
        fields,
        where_filter=None,
        num_relevant=2,
    ):
        try:
            query = (
                self.client.query.get(class_name, fields)
                .with_near_vector(vector)
                .with_limit(num_relevant)
                .with_additional(["certainty", "id"])
            )
            if where_filter:
                query.with_where(where_filter)
            results = query.do()

            if len(results["data"]["Get"][class_name]) > 0:
                return results["data"]["Get"][class_name]
            else:
                return None

        except Exception as err:
            print(f"Unexpected error {err=}, {type(err)=}")
            return None

    def retrieve_episode(self, agent_uuid, episode_uuid):
        try:
            query = self.client.query.get(
                "Episode", ["overview", "content", "child_episodes_uuid", "created_at"]
            ).with_additional(["id"])
            filter = {
                "operator": "And",
                "operands": [
                    self._get_id_filter(id=episode_uuid),
                    self._get_agent_filter(agent_id=agent_uuid),
                ],
            }
            query.with_where(filter)
            results = query.do()

            if len(results["data"]["Get"]["Episode"]) > 0:
                id = results["data"]["Get"]["Episode"][0]["_additional"]["id"]
                return results["data"]["Get"]["Episode"][0]
            else:
                return None
        except Exception as err:
            print(f"Unexpected error {err=}, {type(err)=}")
            return None

    def get_episode(self, agent_uuid, episode_uuid: str) -> Optional[Episode]:
        stored_episode = self.retrieve_episode(
            agent_uuid=agent_uuid, episode_uuid=episode_uuid
        )
        if stored_episode:
            child_episodes = []
            for child_episode_uuid in stored_episode["child_episodes_uuid"]:
                child_episodes.append(
                    self.get_episode(
                        agent_uuid=agent_uuid, episode_uuid=child_episode_uuid
                    )
                )
            episode = Episode(
                overview=stored_episode["overview"], content=stored_episode["content"]
            )
            episode._creation_time = stored_episode["created_at"]
            episode.add_child_episodes(episodes=child_episodes)
            episode.link_to_uuid(uuid=episode_uuid)
            return episode
        return None

    def search_episode(
        self, query, agent_uuid, num_relevant=1, certainty=0.9
    ) -> Optional[Episode]:
        vector = get_ada_embedding(query)
        # Get the most similar overview
        most_similar_contents = self._get_relevant(
            vector=({"vector": vector, "certainty": certainty}),
            class_name="Episode",
            fields=["content", "overview", "child_episodes_uuid", "created_at"],
            num_relevant=num_relevant,
        )
        if most_similar_contents:
            stored_episode = most_similar_contents[0]
            return self.get_episode(
                agent_uuid=agent_uuid, episode_uuid=stored_episode["_additional"]["id"]
            )
        return None

    def create_episode(
        self,
        overview,
        content,
        capability,
        action,
        agent_uuid,
        team_uuid,
        created_at,
        child_episodes_uuid,
    ):
        value = f"{overview}: {content}"
        vector = get_ada_embedding(value)
        episode_uuid = self.client.data_object.create(
            data_object={
                "overview": overview,
                "content": content,
                "capability": capability,
                "action": action,
                "created_at": created_at,
                "child_episodes_uuid": child_episodes_uuid,
            },
            class_name="Episode",
            vector=vector,
        )
        # Link agent to episode
        self.update_cross_reference(
            uuid=episode_uuid,
            reference_object_uuid=agent_uuid,
            field_name="agent",
            class_name="Episode",
            cross_reference_name="Agent",
            override=True,
        )
        # Link team to episode
        self.update_cross_reference(
            uuid=episode_uuid,
            reference_object_uuid=team_uuid,
            field_name="team",
            class_name="Episode",
            cross_reference_name="Team",
            override=True,
        )
        return episode_uuid

    def store_episode(
        self,
        agent_uuid: str,
        team_uuid: str,
        overview: str,
        content: str,
        capability: str,
        action: str,
        created_at: str,
        child_episodes_uuid: List[str] = [],
    ):
        episode_uuid = self.create_episode(
            overview=overview,
            content=content,
            capability=capability,
            action=action,
            agent_uuid=agent_uuid,
            team_uuid=team_uuid,
            created_at=created_at,
            child_episodes_uuid=child_episodes_uuid,
        )
        for child_episode_uuid in child_episodes_uuid:
            # Add parent as cross-reference for each child
            self.update_cross_reference(
                uuid=child_episode_uuid,
                reference_object_uuid=episode_uuid,
                field_name="meta_episode",
                class_name="Episode",
                cross_reference_name="Episode",
                override=True,
            )
        return episode_uuid

    def update_cross_reference(
        self,
        uuid: str,
        reference_object_uuid: str,
        field_name: str,
        class_name: str,
        cross_reference_name: str,
        override: bool = True,
    ):
        # Create a new instance of the cross reference class
        if override:
            self.client.data_object.reference.update(
                from_uuid=uuid,
                from_property_name=field_name,
                to_uuids=[reference_object_uuid],
                from_class_name=class_name,
                to_class_names=cross_reference_name,
            )
        else:
            self.client.data_object.reference.add(
                from_uuid=uuid,
                from_property_name=field_name,
                to_uuid=reference_object_uuid,
                from_class_name=class_name,
                to_class_name=cross_reference_name,
            )

    def recursive_search(self, overview, query, certainty=0.9, depth=1):
        """This method uses remember to first search for the parent overview and then do a recursive search"""

        # First search for most similar episode
        final_query = f"{overview}: {query}"
        vector = get_ada_embedding(final_query)
        # Get the most similar overview
        result = self._get_relevant(
            vector=({"vector": vector, "certainty": certainty}),
            class_name="Episode",
            fields=["overview, content"],
            num_relevant=1,
        )
        episodes = []
        if result:
            episodes.append(result[0]["content"])
            episodes.extend(
                self.remember(final_query, result[0]["overview"], certainty, depth)
            )
        return episodes

    def remember(self, query, parent_overview, certainty=0.9, depth=1):
        """
        Traverse a tree of episodes, searching for the most similar content to the given query at each level.

        This function starts from the given parent_overview and traverses the tree to a specified depth,
        looking for episodes with content similar to the query. The similarity is determined by embeddings
        and a specified certainty threshold.

        Args:
            query (str): The query to find similar content for.
            parent_overview (str): The overview to start the traversal from.
            certainty (float, optional): The similarity threshold for content, default is 0.9.
            depth (int, optional): The maximum depth of the traversal, default is 1.

        Returns:
            list: A list of relevant content found during the traversal.
        """

        episodes = []
        vector = get_ada_embedding(query)
        while depth > 0:
            result = self._get_relevant(
                vector=({"vector": vector, "certainty": certainty}),
                class_name="Episode",
                fields=["overview, content"],
                num_relevant=1,
                where_filter=self._get_meta_episode_overview_filter(parent_overview),
            )
            if result:
                parent_overview = result[0]["overview"]
                relevant_content = result[0]["content"]
                episodes.append(relevant_content)
                depth -= 1
            else:
                break
        return episodes

    def _get_meta_episode_overview_filter(self, overview):
        filter_obj = {
            "path": ["meta_episode", "Episode", "overview"],
            "operator": "Equal",
            "valueText": overview,
        }
        return filter_obj

    def _get_agent_filter(self, agent_id):
        agent_filter_object = {
            "path": ["agent", "Agent", "id"],
            "operator": "Equal",
            "valueString": agent_id,
        }
        return agent_filter_object

    def _get_team_filter(self, team_id):
        team_filter_object = {
            "path": ["team", "Team", "id"],
            "operator": "Equal",
            "valueString": team_id,
        }
        return team_filter_object

    def _get_id_filter(self, id):
        id_filter_object = {
            "path": ["id"],
            "operator": "Equal",
            "valueString": id,
        }
        return id_filter_object
