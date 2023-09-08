import logging
import os
from colorama import Fore

from newrail.utils.print_utils import (
    print_to_console,
)


class Logger:
    _instance = None

    LEVEL_COLORS = {
        "debug": Fore.BLUE,
        "info": Fore.GREEN,
        "warning": Fore.YELLOW,
        "error": Fore.RED,
        "critical": Fore.MAGENTA,
    }

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, protagonist=None):
        if not hasattr(self, "initialized"):
            self.initialized = True
            self.loggers = {}
        if protagonist and not hasattr(self, "protagonist"):
            self.protagonist = protagonist
        elif not protagonist and not hasattr(self, "protagonist"):
            raise ValueError(
                "A protagonist is needed for first instantiation of Logger"
            )

    def _create_logger(self, logger_name):
        # check if logger with given name already exists
        if logger_name in logging.Logger.manager.loggerDict:
            logger = logging.getLogger(logger_name)
        else:
            # create new logger with given name
            logger = logging.getLogger(logger_name)
            logger.propagate = False
            logger.setLevel(logging.INFO)

            os.makedirs(os.path.dirname(logger_name), exist_ok=True)

            # create file handler which logs even debug messages
            fh = logging.FileHandler(f"{logger_name}.log")
            fh.setLevel(logging.INFO)

            # create formatter and add it to the handler
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            fh.setFormatter(formatter)

            # add the handlers to the logger
            logger.addHandler(fh)

            # store the file handler
            self.file_handler = fh

        return logger

    def create_logger(self, name: str, folder: str, process_name: str) -> "Logger":
        key = (name, process_name)
        if key not in self.loggers:
            logger_name = os.path.join(folder, name, process_name)
            child_logger = self._create_logger(logger_name)
            self.loggers[key] = child_logger
        return self.loggers[key]

    def has_privileges(self, name: str) -> bool:
        return name == self.protagonist

    def update_protagonist(self, name: str):
        self.protagonist = name

    def log(
        self,
        name: str,
        process_name: str,
        message: str,
        title: str = "",
        color: str = "",
        log_level: str = "",
        should_print: bool = False,
        privileged: bool = False,
    ):
        if not title:
            title = log_level.upper()
        if not color:
            color = self.LEVEL_COLORS.get(log_level, "")
        is_privileged = self.has_privileges(name) or privileged
        if should_print and is_privileged:
            print_to_console(title=title, title_color=color, content=str(message))
        key = (name, process_name)
        if log_level == "debug":
            self.loggers[key].log(message)
        elif log_level == "warning":
            self.loggers[key].warning(message)
        elif log_level == "error":
            self.loggers[key].error(message)
        elif log_level == "critical":
            self.loggers[key].critical(message)
        else:
            self.loggers[key].info(message)
