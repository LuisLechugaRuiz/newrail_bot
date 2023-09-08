import yaml
import os
import shutil

from newrail.config.config import Config


class OrganizationConfig(object):
    def __init__(
        self,
        organization_name: str,
        organization_id: str,
        max_concurrent_agents: int,
    ):
        self.organization_name = organization_name
        self.organization_id = organization_id
        self.max_concurrent_agents = max_concurrent_agents
        self.save()

    @classmethod
    def get_config_file_path(cls, folder):
        return os.path.join(folder, "config.yaml")

    @property
    def folder(self) -> str:
        self.organization_name = (
            self.organization_name.lower().replace(" ", "_")
            if self.organization_name and " " in self.organization_name
            else self.organization_name
        )
        return os.path.join(Config().organizations_folder, self.organization_name)

    @classmethod
    def load(cls, folder):
        try:
            config_file_path = cls.get_config_file_path(folder)
            if Config().debug_mode:
                print("Loading organization config from", config_file_path)
            with open(config_file_path) as file:
                config_params = yaml.load(file, Loader=yaml.FullLoader)
                instance = cls(**config_params)
                return instance
        except FileNotFoundError:
            return None

    def remove(self):
        if os.path.isdir(self.folder):
            shutil.rmtree(self.folder)
            return True
        else:
            return False

    def save(self):
        config_file = self.get_config_file_path(self.folder)
        os.makedirs(os.path.dirname(config_file), exist_ok=True)
        config = {attr: getattr(self, attr) for attr in vars(self)}
        with open(config_file, "w") as file:
            yaml.dump(config, file)
