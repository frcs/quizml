"""Shared path lookup for QuizML inputs and assets."""

import os
from pathlib import Path


def find_path(path, search_dirs):
    """Return the first existing path and its search-directory index.

    Absolute paths are checked directly and use an index of ``None``. Relative
    paths are checked in the order supplied by the caller. Returning the index
    lets callers preserve behavior that depends on which search directory won.
    """
    requested = Path(path).expanduser()
    if requested.is_absolute():
        candidate = Path(os.path.realpath(requested))
        return (candidate, None) if candidate.exists() else None

    for index, directory in enumerate(search_dirs):
        candidate = Path(
            os.path.realpath(Path(directory).expanduser() / requested)
        )
        if candidate.exists():
            return candidate, index
    return None
