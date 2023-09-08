import os

from newrail.organization.utils.logger.logger import Logger


class OrgLogger:
    def __init__(
        self,
        organization_name: str,
        organization_folder: str,
        process_name: str,
    ):
        self.organization_name = organization_name
        self.organization_folder = organization_folder
        self.process_name = process_name
        Logger().create_logger(
            name=organization_name,
            folder=organization_folder,
            process_name=process_name,
        )

    def create_logger(self, process_name: str, folder: str = "") -> "OrgLogger":
        if folder:
            folder = str(os.path.join(self.organization_folder, folder))
        else:
            folder = self.organization_folder
        Logger().create_logger(
            name=self.organization_name,
            folder=folder,
            process_name=process_name,
        )
        return OrgLogger(
            organization_name=self.organization_name,
            organization_folder=folder,
            process_name=process_name,
        )

    def update_protagonist(self, protagonist_name: str):
        Logger().update_protagonist(name=protagonist_name)

    def log(self, message, log_level="", should_print=False):
        Logger().log(
            name=self.organization_name,
            process_name=self.process_name,
            message=message,
            log_level=log_level,
            should_print=should_print,
            privileged=True,
        )

    def log_debug(self, message, should_print=False):
        Logger().log(
            name=self.organization_name,
            process_name=self.process_name,
            message=message,
            log_level="debug",
            should_print=should_print,
        )

    def log_info(self, message, should_print=False):
        Logger().log(
            name=self.organization_name,
            process_name=self.process_name,
            message=message,
            log_level="info",
            should_print=should_print,
        )

    def log_warning(self, message, should_print=False):
        Logger().log(
            name=self.organization_name,
            process_name=self.process_name,
            message=message,
            log_level="warning",
            should_print=should_print,
        )

    def log_error(self, message, should_print=False):
        Logger().log(
            name=self.organization_name,
            process_name=self.process_name,
            message=message,
            log_level="error",
            should_print=should_print,
        )

    def log_critical(self, message, should_print=False):
        Logger().log(
            name=self.organization_name,
            process_name=self.process_name,
            message=message,
            log_level="critical",
            should_print=should_print,
        )
