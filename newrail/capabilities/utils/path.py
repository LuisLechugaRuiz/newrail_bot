from pathlib import Path
from typing import Union

from newrail.config.config import Config


def safe_path_join(base: Union[str, Path], *paths: Union[str, Path]) -> Path:
    """Join one or more path components, asserting the resulting path is within the workspace.
    Args:
        base (Union[str, Path]): The base path
        *paths (Union[str, Path]): The paths to join to the base path
    Returns:
        Path: The joined path
    """
    base = Path(base)  # Ensure base is a Path object
    joined_path = base.joinpath(*paths).resolve()

    if Config().restrict_to_workspace and not joined_path.is_relative_to(base):
        raise ValueError(
            f"Attempted to access path '{joined_path}' outside of workspace '{base}'."
        )

    return joined_path
