"""Text processing functions"""
import os
from pathlib import Path
from typing import Tuple

from newrail.capabilities.utils.path import safe_path_join


class TextProcessor(object):
    """A class used to read text and save it to long term memory"""

    def __init__(
        self,
    ):
        pass

    @staticmethod
    def read_file(folder, filename: str) -> str:
        """Read a file and return the contents
        Args:
            folder (str): The folder of the file
            filename (str): The name of the file to read
        Returns:
            str: The contents of the file
        """
        try:
            filepath = safe_path_join(folder, filename)
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            return content
        except Exception as e:
            return f"Error: {str(e)}"

    @classmethod
    def write_to_file(cls, filepath: Path, text: str) -> Tuple[bool, str]:
        """Write text to a file
        Args:
            filepath (Path): File path where the text should be written
            text (str): The text to write to the file
        Returns:
            str: A message indicating success or failure
        """
        try:
            cls.create_file(filepath)  # Create the file if it doesn't exist
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(text)
            return True, "File written to successfully."
        except Exception as e:
            return False, f"Error: {str(e)}"

    @classmethod
    def create_file(cls, filepath: Path):
        try:
            directory = os.path.dirname(filepath)
            if not os.path.exists(directory):
                os.makedirs(directory)
            return True, "File created successfully."
        except Exception as e:
            return False, f"Error: {str(e)}"
