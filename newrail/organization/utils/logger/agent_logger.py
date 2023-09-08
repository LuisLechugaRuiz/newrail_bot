from colorama import Fore
import os

from newrail.agent.config.stage import Stage
from newrail.agent.config.config import AgentConfig
from newrail.organization.utils.logger.logger import Logger


class AgentLogger:
    STAGE_COLORS = {
        Stage.PLANNING: Fore.YELLOW,
        Stage.ATTENTION: Fore.BLUE,
        Stage.EXECUTION: Fore.GREEN,
    }

    def __init__(
        self,
        agent_name: str,
        agent_config: AgentConfig,
        agent_folder: str,
        process_name: str,
    ):
        self.agent_name = agent_name
        self.agent_folder = agent_folder
        self.process_name = process_name
        self.agent_config = agent_config
        self.logger = Logger(protagonist=agent_name).create_logger(
            name=agent_name, folder=agent_folder, process_name=process_name
        )

    def create_logger(self, process_name: str, folder: str = "") -> "AgentLogger":
        if folder:
            folder = str(os.path.join(self.agent_folder, folder))
        else:
            folder = self.agent_folder
        Logger().create_logger(
            name=self.agent_name,
            folder=folder,
            process_name=process_name,
        )
        return AgentLogger(
            agent_name=self.agent_name,
            agent_config=self.agent_config,
            agent_folder=folder,
            process_name=process_name,
        )

    def log(self, message, log_level="", should_print=False):
        agent_stage = self.agent_config.get_stage()
        title = f"{self.agent_name} - {agent_stage.name}"
        color = self.STAGE_COLORS[agent_stage]
        Logger().log(
            name=self.agent_name,
            process_name=self.process_name,
            message=message,
            title=title,
            color=color,
            log_level=log_level,
            should_print=should_print,
        )

    def log_debug(self, message, should_print=False):
        Logger().log(
            name=self.agent_name,
            process_name=self.process_name,
            message=message,
            log_level="debug",
            should_print=should_print,
        )

    def log_info(self, message, should_print=False):
        Logger().log(
            name=self.agent_name,
            process_name=self.process_name,
            message=message,
            log_level="info",
            should_print=should_print,
        )

    def log_warning(self, message, should_print=False):
        Logger().log(
            name=self.agent_name,
            process_name=self.process_name,
            message=message,
            log_level="warning",
            should_print=should_print,
        )

    def log_error(self, message, should_print=False):
        Logger().log(
            name=self.agent_name,
            process_name=self.process_name,
            message=message,
            log_level="error",
            should_print=should_print,
        )

    def log_critical(self, message, should_print=False):
        Logger().log(
            name=self.agent_name,
            process_name=self.process_name,
            message=message,
            log_level="critical",
            should_print=should_print,
        )
