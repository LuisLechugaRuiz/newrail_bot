import asyncio
import threading
from typing import Optional
from typing import List

from supabase.client import create_client
from supabase.lib.client_options import ClientOptions
from realtime.connection import Socket
from realtime.types import Callback

from newrail.config.config import Config


class Channel:
    def __init__(self, topic, event_type, callback):
        self.topic = topic
        self.event_type = event_type
        self.callback = callback


class SupabaseHandler:
    def __init__(self):
        self.supabase_url = Config().supabase_url
        self.supabase_key = Config().supabase_key
        self.public_client = create_client(self.supabase_url, self.supabase_key)
        self.user_client = create_client(
            self.supabase_url, self.supabase_key, options=ClientOptions(schema="auth")
        )
        self.realtime_url: str = f"{self.supabase_url}/realtime/v1/websocket?apikey={self.supabase_key}&vsn=1.0.0".replace(
            "http", "ws"
        )
        self.channels: List[Channel] = []
        self.listen_task: Optional[threading.Thread] = None

    def subscribe_to_channel(
        self, schema: str, table_name: str, event_type: str, callback: Callback
    ):
        self.channels.append(
            Channel(
                topic=f"realtime:{schema}:{table_name}",
                event_type=event_type,
                callback=callback,
            )
        )

    def start_listen_task(self):
        new_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(new_loop)
        self.socket = Socket(url=self.realtime_url)
        self.socket.connect()
        for channel in self.channels:
            self.socket.set_channel(topic=channel.topic).join().on(
                channel.event_type, channel.callback
            )
        new_loop.run_until_complete(self.socket.listen())
        new_loop.close()

    def start_realtime_listener(self):
        if not self.listen_task:
            self.listen_task = threading.Thread(target=self.start_listen_task)
            self.listen_task.start()

    def create_agent(self, **data):
        existing_agent = (
            self.public_client.table("agents")
            .select("*")
            .eq("name", data["name"])
            .eq("organization_id", data["organization_id"])
            .execute()
        )
        if existing_agent:
            self.update_agent(**data)
        else:
            self.public_client.table("agents").insert([data]).execute()

    def create_team(self, **data):
        existing_team = (
            self.public_client.table("teams").select("*").eq("id", data["id"]).execute()
        )
        if existing_team:
            self.public_client.table("teams").update(data).eq(
                "id", data["id"]
            ).execute()
        else:
            self.public_client.table("teams").insert([data]).execute()

    def create_organization(self, **data):
        existing_org = (
            self.public_client.table("organizations")
            .select("*")
            .eq("id", data["id"])
            .execute()
        )
        if existing_org:
            self.public_client.table("organizations").update(data).eq(
                "id", data["id"]
            ).execute()
        else:
            self.public_client.table("organizations").insert([data]).execute()

    def create_user(self, **data):
        existing_user = (
            self.public_client.table("users").select("*").eq("id", data["id"]).execute()
        )
        if existing_user:
            self.public_client.table("users").update(data).eq(
                "id", data["id"]
            ).execute()
        else:
            self.public_client.table("users").insert([data]).execute()

    def create_task(self, **data):
        self.public_client.table("tasks").insert([data]).execute()

    def create_capability(self, **data):
        existing_capability = (
            self.public_client.table("capabilities")
            .select("*")
            .eq("id", data["id"])
            .eq("organization_id", data["organization_id"])
            .execute()
        )
        if existing_capability:
            self.public_client.table("capabilities").update(data).eq(
                "id", data["id"]
            ).execute()
        else:
            self.public_client.table("capabilities").insert([data]).execute()

    def create_team_invocations(self, **data):
        self.public_client.table("team_invocations").insert([data]).execute()

    def delete_team_invocations(self, team_invocations_id: str):
        self.public_client.table("team_invocations").delete().eq(
            "id", team_invocations_id
        ).execute()

    def link_capability(self, **data):
        same_capability = (
            self.public_client.table("agent_capabilities")
            .select("*")
            .eq("agent_id", data["agent_id"])
            .eq("capability_id", data["capability_id"])
            .eq("organization_id", data["organization_id"])
            .execute()
        )
        if same_capability:
            print("Capability already linked")
        else:
            self.public_client.table("agent_capabilities").insert([data]).execute()

    def get_capabilities(self, organization_id):
        return (
            self.public_client.table("capabilities")
            .select("*")
            .eq("organization_id", organization_id)
            .execute()
        )

    def get_all_agents(self, organization_id):
        return (
            self.public_client.table("agents")
            .select("*")
            .eq("organization_id", organization_id)
            .execute()
        )

    def get_agent(self, organization_id, agent_name):
        return (
            self.public_client.table("agents")
            .select("*")
            .eq("organization_id", organization_id)
            .eq("name", agent_name)
            .execute()
            .data
        )

    def get_agent_from_id(self, organization_id, agent_id):
        return (
            self.public_client.table("agents")
            .select("*")
            .eq("organization_id", organization_id)
            .eq("id", agent_id)
            .execute()
            .data
        )

    def get_agent_capabilities(self, organization_id, agent_name, team_name):
        return (
            self.public_client.table("agents")
            .select("*, capabilities(name)")
            .eq("organization_id", organization_id)
            .eq("name", agent_name)
            .eq("team_name", team_name)
            .execute()
            .data
        )

    def get_supervised_agent(
        self,
        organization_id,
        supervisor_name,
    ):
        return (
            self.public_client.table("agents")
            .select("*")
            .eq("organization_id", organization_id)
            .eq("supervisor_name", supervisor_name)
            .execute()
            .data
        )

    def get_team(self, organization_id, team_name):
        return (
            self.public_client.table("teams")
            .select("*, team_invocations(*)")
            .eq("organization_id", organization_id)
            .eq("name", team_name)
            .execute()
            .data
        )

    def get_team_from_id(self, organization_id, team_id):
        return (
            self.public_client.table("teams")
            .select("*")
            .eq("organization_id", organization_id)
            .eq("id", team_id)
            .execute()
            .data
        )

    def get_team_invocations(self, organization_id, team_name):
        return (
            self.public_client.table("team_invocations")
            .select("*")
            .eq("organization_id", organization_id)
            .eq("team_name", team_name)
            .execute()
            .data
        )

    def get_organization(self, organization_id):
        return (
            self.public_client.table("organizations")
            .select("*")
            .eq("id", organization_id)
            .execute()
            .data
        )

    def get_tasks(self, organization_id, agent_id):
        return (
            self.public_client.table("tasks")
            .select("*")
            .eq("organization_id", organization_id)
            .eq("agent_id", agent_id)
            .execute()
            .data
        )

    # TODO: Add here name of the user when we add it to supabase.
    def get_user_from_id(self, user_id):
        return (
            self.user_client.table("users").select("*").eq("id", user_id).execute().data
        )

    def send_notification(self, **data):
        self.public_client.table("agent_notifications").insert([data]).execute()

    def send_event(self, **data):
        self.public_client.table("agent_incoming_events").insert([data]).execute()

    def update_agent(self, **agent_data):
        self.public_client.table("agents").update(agent_data).eq(
            "id", agent_data["id"]
        ).execute()

    def update_team_invocations(self, team_invocations_id: str, status: str):
        self.public_client.table("team_invocations").update({"status": status}).eq(
            "id", team_invocations_id
        ).execute()

    def update_task(self, task_id: str, status: str):
        self.public_client.table("tasks").update({"status": status}).eq(
            "id", task_id
        ).execute()
