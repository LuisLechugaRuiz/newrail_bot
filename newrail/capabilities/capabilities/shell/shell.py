import os
import re
import pexpect
from pathlib import Path
from typing import List

from newrail.capabilities.utils.decorators import (
    action_decorator,
    context_decorator,
)
from newrail.capabilities.capability import Capability

WORKSPACE = "data"


class Shell(Capability):
    """
    Manage the execution of shell commands in the current workspace.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.workspace_root = Path(os.path.join(self.org_folder, WORKSPACE))
        self.workspace = self.workspace_root
        os.makedirs(self.workspace, exist_ok=True)
        self.shell = pexpect.spawn("/bin/bash --norc --noprofile", encoding="utf-8")
        self.shell.sendline(f"export PWD={self.workspace}")
        self.shell.sendline(f"cd {self.workspace}")

    def _update_workspace(self):
        self.shell.sendline("pwd")
        current_path = self.shell.before.strip().splitlines()[-1]
        self.workspace = Path(current_path)

    @context_decorator
    def current_shell_path(self) -> str:
        """Get the current shell path"
        Returns:
            str: The current shell path
        """

        self._update_workspace()
        message = f"You should always work on folders at {self.workspace_root}.\nCurrent path: {self.workspace}"
        return message

    @action_decorator
    def execute_shell(self, command_lines: List[str]) -> str:
        """Execute a list of shell commands"
        Args:
            command_lines (List[str]): The list of command lines to execute
        Returns:
            str: The output of the commands
        """
        output = []

        for command_line in command_lines:
            self.shell.sendline(command_line)
            cmd_output = self.shell.before.strip()

            self._update_workspace()
            if not str(self.workspace).startswith(str(self.workspace_root)):
                self.shell.sendline(f"cd {self.workspace_root}")
                return f"Error: command: {command_line} tried to leave workspace. You should always work inside workspace: {self.workspace_root}"

            output.append(cmd_output)

        return "\n".join(output)
