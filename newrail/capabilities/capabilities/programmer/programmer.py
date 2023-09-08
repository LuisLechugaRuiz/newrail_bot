"""Programmer class to analyze, improve, execute or create test"""
import json
import os

from pathlib import Path
from typing import Dict, List


from newrail.capabilities.capability import Capability
from newrail.capabilities.capabilities.programmer.prompts.create_class_prompt import (
    DEF_PROGRAMMER_COMMAND,
)
from newrail.capabilities.capabilities.programmer.prompts.create_test_prompt import (
    DEF_TEST_PROGRAMMER_COMMAND,
)
from newrail.capabilities.utils.docker_run import DockerRun
from newrail.capabilities.utils.path import safe_path_join
from newrail.capabilities.utils.processing.text_processor import TextProcessor
from newrail.capabilities.utils.decorators import (
    action_decorator,
    context_decorator,
)
from newrail.utils.chat.chat import Chat


class Programmer(Capability):
    """
    Create, improve or execute code and create test. Useful when you need to create or improve code.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.docker = DockerRun("python:3-alpine", self.logger)
        # TODO: Make this generic to get data as the main entry point of information for the org (adapt it when Notion / Jira are implemented).
        self.code_folder = os.path.join(self.org_folder, "data/code")

        os.makedirs(self.code_folder, exist_ok=True)

    @context_decorator
    def get_class_files(self) -> str:
        """
        Get a human-readable message with class name - file path at current workspace.

        Returns:
            str: A human-readable message with class name - file path at current workspace.
        """

        class_files_msg = (
            "\nThese are the current class - file path at current workspace:\n"
        )
        class_files_dict = self.get_class_files_dict()
        for class_name, file_path in class_files_dict.items():
            class_files_msg += f"{class_name}: {file_path}"

        return class_files_msg

    # TODO: FIX ME!!
    @action_decorator
    def execute_python_file(self, file: str) -> str:
        """
        Executes a given Python file.

        Args:
            file (str): Name of the Python file to be executed, including the .py extension.

        Returns:
            str: The output logs of the executed Python file. In case of an error (e.g., invalid file type or non-existent file),
                an error message is returned instead.
        """

        print(f"Executing file '{file}' in workspace '{self.code_folder}'")

        if not file.endswith(".py"):
            return "Error: Invalid file type. Only .py files are allowed."

        file_path = safe_path_join(Path(self.code_folder), file)

        if not os.path.isfile(file_path):
            return f"Error: File '{file}' does not exist."

        self.logger.log(f"Running file: {file}")
        logs = self.docker.run_container(
            f"python {file}",
            "/workspace",
            {
                os.path.abspath(self.code_folder): {
                    "bind": "/workspace",
                    "mode": "ro",
                }
            },
        )
        self.logger.log(f"Result: {logs}")
        return logs

    # TODO: Improve this with our own way.
    # @action_decorator
    def improve_code(self, class_name: str, suggestions: List[str]) -> str:
        """
        A function that takes a class name and suggestions and improves the code of the class based on suggestions.

        Args:
            code (str): Code to be improved.
            suggestions (List[str]): A list of suggestions around what needs to be improved.
        Returns:
            str: Improved code.
        """

        class_file_dict = self.get_class_files_dict()
        code = TextProcessor.read_file(self.code_folder, class_file_dict[class_name])
        function_string = (
            "def generate_improved_code(suggestions: List[str], code: str) -> str:"
        )
        args = [json.dumps(suggestions), code]
        description_string = (
            "Improves the provided code based on the suggestions"
            " provided, making no other changes."
        )
        return call_ai_function(function_string, args, description_string)

    @action_decorator
    def create_test(self, class_name: str, test_cases: List[str], filename: str) -> str:
        """
        Create a test for a specific class and save it in a test file.

        Args:
            class_name (str): The name of the class to create tests for.
            test_cases (List[str]): A list of test cases.
            filename (str): The name of the file to save the test code in.

        Returns:
            str: The code of the created test.
        """
        class_file_dict = self.get_class_files_dict()
        code = TextProcessor.read_file(self.code_folder, class_file_dict[class_name])
        create_test_prompt = DEF_TEST_PROGRAMMER_COMMAND.format(
            code=code, test_cases=test_cases
        )
        test_code = Chat.get_response(
            system=create_test_prompt,
            user="Remember to only return the code.",
            smart_llm=True,
        )
        result = self.save_code(test_code, filename)
        result += f" Generated test code: {test_code}"
        return result

    @action_decorator
    def create_code(
        self,
        class_name: str,
        description: str,
        functions: List[Dict[str, str]],
        filename: str,
    ) -> str:
        """
        Generates a Python class code given the class name, description, functions, and filename. The method
        creates a class definition, writes function signatures with docstrings, and saves the code to the specified file.

        Args:
            class_name (str): The name of the class to create.
            description (str): The Google-style docstring of the class, including a detailed description, Args, and Returns.
            functions (List[Dict[str, str]]): A list of dictionaries, where each dictionary contains a function signature as a key and a description as a value.
            filename (str): The name of the file to save the code in.

        Returns:
            str: The code of the created class.
        """
        edited_functions = ""
        for function_dict in functions:
            if not isinstance(function_dict, dict):
                return "Error: functions must be a list of dictionaries with the function signature as key and and the description as value."
            for signature, docstring in function_dict.items():
                edited_functions += f"{signature}\n{docstring}\n"
        create_class_prompt = DEF_PROGRAMMER_COMMAND.format(
            class_name=class_name, description=description, functions=edited_functions
        )
        code = Chat.get_response(
            system=create_class_prompt,
            user="Remember to only return the code.",
            smart_llm=True,
        )
        result = self.save_code(code, filename)
        result += (
            f" Generated untested code: {code}\n. Please create a test for this class."
        )
        return result

    def get_class_files_dict(self) -> Dict[str, str]:
        """
        Get a dictionary of file paths and class names for current workspace.

        Returns:
            Dict[str, str]: A dictionary of file paths and class names.
        """
        class_files_dict = {}

        for root, _, files in os.walk(self.code_folder):
            for file in files:
                if file.endswith(".py"):
                    file_path = os.path.join(root, file)
                    with open(file_path) as f:
                        content = f.read()
                        for line in content.splitlines():
                            if line.startswith("class"):
                                class_name = (
                                    line.split(" ")[1].split("(")[0].rstrip(":")
                                )
                                class_files_dict[class_name] = file_path

        return class_files_dict

    def save_code(self, code: str, filename: str) -> str:
        """
        Save code to a file.

        Args:
            code (str): The code to save.
            filename (str): The name of the file to save the code in.

        Returns:
            str: The result of the save operation.
        """

        # Remove triple backticks if they are present at the beginning of the generated code
        if code.startswith("```python"):
            code = code[9:]  # Remove the first 9 characters ("```python\n")
        if code.endswith("```"):
            code = code[:-3]  # Remove the last 3 characters ("```")
        filepath = safe_path_join(Path(self.code_folder), filename)
        success, message = TextProcessor.write_to_file(filepath, code)
        if success:
            result = f"Code saved on file {filepath}"
        else:
            result = f"Failed to save code on file: {filepath}, due to: {message}"
        return result
