"""An example of a plugin"""
# To illustrate the example all the comments are used as instructions.

# This are some libraries that we need to execute the code.
import os
from pathlib import Path
from typing import Union

# You should always import this library
from newrail.execution.actions.plugins.plugin import Plugin

# This decorator exposes the actions that the model can use from the plugin.
# Use it on top of the function that you want to expose.
from newrail.execution.utils.plugin_decorators import action_decorator

# This decorator is called to expose info to the user of plugin during execution time.
# Use it to expose relevant information as the function will be called before the plugin is used by the user.
from newrail.execution.utils.plugin_decorators import context_decorator


# Remember to use Plugin as base class.
class PluginExample(Plugin):
    """
    A description which describes the functionality of the plugin.

    e.g:
    A plugin to read, write, or search local files. Useful when you need to access to local file.
    Using this plugin you can read all the info stored on files or create new files. You will not need to parse or transform the data.
    """

    # The constructor should be always built this way to transfer the needed data to the base class. So you always call super().__init__(*args, **kwargs)
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Here you can add any other initialization you need.
        # E.g:
        self.workspace = Path(os.path.join(self.org_folder, "data"))

    # This is an example of the use of context_decorator. This function will be called to expose relevant info for the plugin usage.
    @context_decorator
    # This function expose the directory structure of the permanent storage.
    def inspect_directory_structure(self) -> str:
        # Here you should always add a decent docstring with Args (if any) and returns as they will be used as instructions to the agent.
        # So we can receive and use the correct arguments. E.g:
        """
        Inspect the directory structure of the permanent storage and return a human-readable representation.

        Returns:
            str: A human-readable representation of the directory structure.
        """
        # This is just an example of a functionality to get the files / directories structure.
        found_files = []

        def process_directory(dir_path, prefix):
            for entry in os.scandir(dir_path):
                if entry.is_file() and not entry.name.startswith("."):
                    found_files.append(f"{prefix} {entry.name}")
                elif entry.is_dir() and not entry.name.startswith("."):
                    found_files.append(f"{prefix} {entry.name}:")
                    process_directory(entry.path, prefix + "  ")

        process_directory(self.workspace, "")

        # The result message is very important as it will be used to fill the Feedback so please be very explicit about what the return value after using the function.
        # In case the user performed an action using this function always expose the result as a string. E.g:
        result_msg = "\nThis is the directory structure:\n" + "\n".join(found_files)
        return result_msg

    # This is an example of the use of action_decorator. The function which has this decorator will be expose to the agent to perform a certain action.
    @action_decorator
    # This function reads a file and returns the content.
    def read_file(self, filename: str) -> str:
        # Remember to provide a detailed docstring with Args and Returns (should always be a string).
        """Read a file and return the contents
        Args:
            filename (str): The name of the file to read
        Returns:
            str: The contents of the file
        """

        try:
            # You can use other helper functions inside the class.
            filepath = self.safe_path_join(self.workspace, filename)
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            # Remember to return a detailed feedback
            return f"File '{filename}' read successfully. Content: {content}"
        except Exception as e:
            # Remember to return it also in case of errors in order to be detected by the agent.
            return f"Error: {str(e)}"

    # This is just a helper method which is not exposed but is useful to help other methods.
    def safe_path_join(self, base: Union[str, Path], *paths: Union[str, Path]) -> Path:
        # Docstring
        """Join one or more path components.
        Args:
            base (Union[str, Path]): The base path
            *paths (Union[str, Path]): The paths to join to the base path
        Returns:
            Path: The joined path
        """
        # Helps to join the path
        base = Path(base)
        joined_path = base.joinpath(*paths).resolve()
        return joined_path
