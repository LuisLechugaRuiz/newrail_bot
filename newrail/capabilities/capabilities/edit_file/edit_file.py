"""Edit file capability"""
from __future__ import annotations

import os
import os.path
import requests
from colorama import Back, Fore
from requests.adapters import HTTPAdapter, Retry

from newrail.config.config import Config
from newrail.capabilities.utils.path import safe_path_join
from newrail.capabilities.utils.decorators import (
    action_decorator,
    context_decorator,
)
from newrail.capabilities.capability import Capability
from newrail.capabilities.utils.processing.text_processor import TextProcessor
from newrail.utils.spinner import Spinner


class EditFile(Capability):
    """
    Read, write, or search local files. Useful when you need to access to local file.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.workspace = Config().organization_data

    @context_decorator
    def inspect_directory_structure(self) -> str:
        """
        Inspect the directory structure of the permanent storage and return a human-readable representation.

        Returns:
            str: A human-readable representation of the directory structure.
        """
        found_files = []

        def process_directory(dir_path, prefix):
            for entry in os.scandir(dir_path):
                if entry.is_file() and not entry.name.startswith("."):
                    found_files.append(f"{prefix} {entry.name}")
                elif entry.is_dir() and not entry.name.startswith("."):
                    found_files.append(f"{prefix} {entry.name}/")
                    process_directory(entry.path, prefix + "  ")

        process_directory(self.workspace, "-")

        # Join the list items with line breaks to create a human-readable format
        if found_files:
            result_msg = "This is the directory structure:\n" + "\n".join(found_files)
        else:
            result_msg = "No directory yet."
        return result_msg

    def get_workspace_path(self, filename):
        return safe_path_join(self.workspace, filename)

    def log_operation(self, operation: str, filename: str) -> None:
        """Log the file operation to the file_logger.txt
        Args:
            operation (str): The operation to log
            filename (str): The name of the file the operation was performed on
        """
        self.logger.log(f"Operation '{operation}' on file '{filename}'")

    @action_decorator
    def append_to_file(self, filename: str, text: str) -> str:
        """Append text to the end of an existing file.
        Args:
            filename (str): The name of the file to append to
            text (str): The content to append to the file, should be a raw string not a reference.
        Returns:
            str: A message indicating success or failure
        """
        try:
            filepath = safe_path_join(self.workspace, filename)
            with open(filepath, "a") as f:
                f.write(text)

            self.log_operation("append", filename)

            return "Text appended successfully."
        except Exception as e:
            return f"Error: {str(e)}"

    @action_decorator
    def create_folder(self, folder_name: str) -> str:
        """Create a folder

        Args:
            folder_name (str): The name of the folder to create
        Returns:
            str: A message indicating success or failure
        """
        try:
            folder_path = safe_path_join(self.workspace, folder_name)
            os.mkdir(folder_path)
            self.log_operation("create", folder_name)
            return "Folder created successfully."
        except Exception as e:
            return f"Error: {str(e)}"

    @action_decorator
    def insert_text(
        self, filename: str, text: str, last_word: str, line_number: int
    ) -> str:
        """Inserts a given text after the last_word in a specified line_number.

        Args:
            filename (str): The name of the file to read.
            text (str): The text to be inserted.
            last_word (str): The word after which the text will be inserted.
            line_number (int): The line number where the text will be inserted.

        Returns:
            str: The contents of the file after insertion.
        """
        try:
            filepath = safe_path_join(self.workspace, filename)
            with open(filepath, "r+", encoding="utf-8") as f:
                lines = f.readlines()
                # Check line number ranges
                if not 1 <= line_number <= len(lines):
                    return f"Error: line_number {line_number} out of range."
                line = lines[line_number - 1]
                if last_word in line:
                    start_index = line.index(last_word) + len(last_word)
                    # insert text after last_word
                    lines[line_number - 1] = (
                        line[:start_index] + " " + text + line[start_index:]
                    )
                else:
                    lines[line_number - 1] = text + " " + line
                f.seek(0)
                f.writelines(lines)
                f.truncate()
            return f"File '{filename}' updated successfully."
        except Exception as e:
            return f"Error: {str(e)}"

    @action_decorator
    def remove_text(
        self,
        filename: str,
        from_line_number: int,
        from_word: str,
        to_line_number: int,
        to_word: str,
    ) -> str:
        """Removes a block of text from from_word at from_line_number to to_word at to_line_number.

        Args:
            filename (str): The name of the file to read.
            from_line_number (int): The line number where the removal starts.
            from_word (str): The word where the removal starts.
            to_line_number (int): The line number where the removal ends.
            to_word (str): The word where the removal ends.

        Returns:
            str: The contents of the file after removal.
        """
        try:
            filepath = safe_path_join(self.workspace, filename)
            with open(filepath, "r+", encoding="utf-8") as f:
                lines = f.readlines()

                # Check line number ranges
                if not 1 <= from_line_number <= len(lines):
                    return f"Error: from_line_number {from_line_number} out of range."
                if not 1 <= to_line_number <= len(lines):
                    return f"Error: to_line_number {to_line_number} out of range."

                # Find start word in from_line
                try:
                    start_index = lines[from_line_number - 1].index(from_word)
                except ValueError:
                    return f"Error: from_word {from_word} not found in line {from_line_number}."

                # Find end word in to_line
                try:
                    end_index = lines[to_line_number - 1].index(to_word) + len(to_word)
                except ValueError:
                    return (
                        f"Error: to_word {to_word} not found in line {to_line_number}."
                    )

                # Remove text
                if from_line_number == to_line_number:
                    # If start and end are in the same line
                    lines[from_line_number - 1] = (
                        lines[from_line_number - 1][:start_index]
                        + lines[from_line_number - 1][end_index:]
                    )
                else:
                    # If start and end are in different lines
                    lines[from_line_number - 1] = lines[from_line_number - 1][
                        :start_index
                    ]
                    lines[to_line_number - 1] = lines[to_line_number - 1][end_index:]

                f.seek(0)
                f.writelines(lines)
                f.truncate()

            return f"File '{filename}' updated successfully."
        except Exception as e:
            return f"Error: {str(e)}"

    @action_decorator
    def delete_file(self, filename: str) -> str:
        """Delete a file
        Args:
            filename (str): The name of the file to delete
        Returns:
            str: A message indicating success or failure
        """
        try:
            filepath = safe_path_join(self.workspace, filename)
            os.remove(filepath)
            self.log_operation("delete", filename)
            return "File deleted successfully."
        except Exception as e:
            return f"Error: {str(e)}"

    # TODO: Verify this.
    # @action_decorator
    def download_file(self, url, filename):
        """Downloads a file
        Args:
            url (str): URL of the file to download
            filename (str): Filename to save the file as
        """
        safe_filename = self.get_workspace_path(filename)
        try:
            message = f"{Fore.YELLOW}Downloading file from {Back.LIGHTBLUE_EX}{url}{Back.RESET}{Fore.RESET}"
            with Spinner(message) as spinner:
                session = requests.Session()
                retry = Retry(
                    total=3, backoff_factor=1, status_forcelist=[502, 503, 504]
                )
                adapter = HTTPAdapter(max_retries=retry)
                session.mount("http://", adapter)
                session.mount("https://", adapter)

                total_size = 0
                downloaded_size = 0

                with session.get(url, allow_redirects=True, stream=True) as r:
                    r.raise_for_status()
                    total_size = int(r.headers.get("Content-Length", 0))
                    downloaded_size = 0

                    with open(safe_filename, "wb") as f:
                        for chunk in r.iter_content(chunk_size=8192):
                            f.write(chunk)
                            downloaded_size += len(chunk)

                            # Update the progress message
                            progress = f"{self.readable_file_size(downloaded_size)} / {self.readable_file_size(total_size)}"
                            spinner.update_message(f"{message} {progress}")

                return f'Successfully downloaded and locally stored file: "{filename}"! (Size: {self.readable_file_size(total_size)})'
        except requests.HTTPError as e:
            return f"Got an HTTP Error whilst trying to download file: {e}"
        except Exception as e:
            return "Error: " + str(e)

    # TODO: MODIFY TEXT PROCESSOR TO INGEST TEXT. WE SHOULD MANAGE ALL THE DATA INGESTED IN MEMORY PROPERLY:
    # TODO: COMMING WITH JIRA/NOTION INTEGRATION.
    # DONE:
    # - INGEST TEXT.
    # - COMPILE A ROLLING SUMMARY (META EPISODE) OF THE INGESTED TEXT.
    # ------------------------------------------------------------------
    # NEXT:
    # - ADD ORDER / METADATA TO THE EPISODE
    # - SAVE THE SUMMARY WITH A OUTLINE TO GUIDE THROUGH THE TEXT? IS THIS NEEDED AFTER NEW EPISODES WITH UUID ?
    # - PROVIDE TO THE USER THE DIFFERENT PARTS WITH A TITLE - UID SO HE CAN GET - MODIFY EACH PART INDENPENDENTLY. IS THIS NEEDED AFTER NEW EPISODES WITH UUID ?
    @action_decorator
    def read_lines_from_file(
        self, folder_path: str, file_name: str, from_line_number: int = 0
    ) -> str:
        """Read a specific line from a file, returns the content as line - content: L{line_number} - {line_content}.

        Args:
            folder_path (str): The path of the folder where the file is located.
            file_name (str): The name of the file to read from.
            from_line_number (int): The initial line number to read, if 0, the whole file will be read.

        Returns:
            str: The content of the specified line or an error message
        """
        filepath = safe_path_join(self.workspace, folder_path, file_name)
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                lines = f.readlines()
                content = ""
                print("DEBUG CONTENT: ", content)
                if from_line_number == 0:
                    for line_number, line in enumerate(lines, start=1):
                        content += f"L{line_number} - {line}"
                elif 1 <= from_line_number <= len(lines):
                    lines = lines[from_line_number - 1 :]
                    for line_number, line in enumerate(lines, start=from_line_number):
                        content += f"L{line_number} - {line}"
                else:
                    return "Error: Line number out of range."
                return content
        except Exception as e:
            return f"Error: {str(e)}"

    @action_decorator
    def create_and_write_on_file(
        self, folder_path: str, file_name: str, text: str
    ) -> str:
        """Create a file in a folder and write the given text to it.

        Args:
            folder_path (str): The path of the folder where the file is located.
            file_name (str): The name of the file to write to.
            text (str): The content of the file, should be a raw string not a reference.
        Returns:
            str: A message indicating success or failure
        """
        filepath = safe_path_join(self.workspace, folder_path, file_name)
        success, message = TextProcessor.write_to_file(filepath, text=text)
        if success:
            self.log_operation("write", file_name)
            return f"Content: {text} written to file: {file_name}."
        return message

    def readable_file_size(self, size, decimal_places=2):
        """Converts the given size in bytes to a readable format.
        Args:
            size: Size in bytes
            decimal_places (int): Number of decimal places to display
        """
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size < 1024.0:
                break
            size /= 1024.0
        return f"{size:.{decimal_places}f} {unit}"
