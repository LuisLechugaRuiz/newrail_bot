from newrail.agent.config.config import AgentConfig


class MockedAgentConfig(AgentConfig):
    def __init__(self, agent_name: str):
        super().__init__(
            created_by_user_id="mocked_user_id",
            id="5e7af5b9-d8d6-4b20-8d6c-3a208875a916",
            name=agent_name,
            organization_id="mocked_organization_id",
            organization_name="mocked_organization",
            mission="mocked_mission",
            capabilities=["mocked_capability"],
            team_id="mocked_team_id",
            team_name="mocked_team",
            is_lead=False,
            supervisor_id=None,
            supervisor_name=None,
        )
