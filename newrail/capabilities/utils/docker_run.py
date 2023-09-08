import docker
from docker.errors import ImageNotFound
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from newrail.organization.utils.logger.agent_logger import AgentLogger


class DockerRun(object):
    def __init__(self, image_name: str, logger: "AgentLogger"):
        self.image_name = image_name
        self.loggers = logger.create_logger("docker_run")
        self.setup_image()

    def setup_image(self):
        try:
            client = self.get_client()
            client.images.get(self.image_name)
            self.loggers.log(f"Image '{self.image_name}' found locally")
            client.close()
        except ImageNotFound:
            self.loggers.log_warning(
                f"Image '{self.image_name}' not found locally, pulling from Docker Hub"
            )
            low_level_client = docker.APIClient()
            for line in low_level_client.pull(
                self.image_name, stream=True, decode=True
            ):
                status = line.get("status")
                progress = line.get("progress")
                if status and progress:
                    self.loggers.log(f"{status}: {progress}")
                elif status:
                    self.loggers.log(status)

    def run_container(self, command: str, working_dir: str, volumes: dict) -> str:
        client = self.get_client()
        container = client.containers.run(
            self.image_name,
            command,
            volumes=volumes,
            working_dir=working_dir,
            stderr=True,
            stdout=True,
            detach=True,
        )

        container.wait()
        logs = container.logs().decode("utf-8")
        container.stop()
        container.remove()
        client.close()

        return logs

    def get_client(self):
        return docker.from_env()
