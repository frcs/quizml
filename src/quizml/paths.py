"""Shared path lookup and file discovery for QuizML inputs, configs, templates, and assets."""

import os
import tempfile
from pathlib import Path

import platformdirs


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


def _expand_dir_variants(directory):
    """Return [<dir>, <dir>/_quizml, <dir>/quizml-templates] for a directory."""
    d = os.path.abspath(directory)
    return [
        d,
        os.path.join(d, "_quizml"),
        os.path.join(d, "quizml-templates"),
    ]


def _ancestor_project_dirs(start_dir):
    """Walk upward from start_dir to discover parent project directories."""
    if not start_dir:
        return []
    cur = Path(start_dir).resolve()
    stop_boundaries = {
        Path.home().resolve(),
        Path(tempfile.gettempdir()).resolve(),
        Path(cur.anchor),
    }
    ancestors = []
    if (cur / ".git").exists():
        return ancestors

    parent = cur.parent
    while parent != cur and parent not in stop_boundaries:
        has_markers = any(
            (parent / marker).exists()
            for marker in ("_quizml", "quizml-templates", "quizml.cfg")
        )
        if has_markers:
            ancestors.extend(_expand_dir_variants(str(parent)))
        if (parent / ".git").exists():
            break
        cur = parent
        parent = cur.parent
    return ancestors


class FileLocator:
    """
    Config file and templates are defined as a relative path, and searched in:
    1. the input YAML's directory (and its `_quizml` / `quizml-templates` subdirs)
    2. parent project directories up to the repository root
    3. the explicit `--config` directory (if provided)
    4. the current working directory (and its `_quizml` / `quizml-templates` subdirs)
    5. the user application config dir
    6. the installed package templates dir
    """

    def __init__(self, cwd=None, base_dir=None, config_dir=None):
        """Sets up default directories to search."""
        self.pkg_template_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "templates")
        )
        self.app_dir = platformdirs.user_config_dir(appname="quizml", appauthor="frcs")
        self.user_template_dir = os.path.join(self.app_dir, "templates")
        self._cwd = os.path.abspath(cwd or os.getcwd())
        self._base_dir = os.path.abspath(base_dir) if base_dir else None
        self._config_dir = os.path.abspath(config_dir) if config_dir else None

    @property
    def cw_dir(self):
        return self._cwd

    @property
    def local_template_dir(self):
        return os.path.join(self.cw_dir, "_quizml")

    @property
    def dirlist(self):
        dirs = []
        candidates = []
        if self._base_dir:
            candidates.extend(_expand_dir_variants(self._base_dir))
            candidates.extend(_ancestor_project_dirs(self._base_dir))
        if self._config_dir:
            candidates.extend(_expand_dir_variants(self._config_dir))
        candidates.extend(_expand_dir_variants(self.cw_dir))
        candidates.extend(_ancestor_project_dirs(self.cw_dir))
        candidates.extend(
            [
                os.path.join(self.app_dir, "_quizml"),
                self.user_template_dir,
                self.pkg_template_dir,
            ]
        )
        for d in candidates:
            if d not in dirs:
                dirs.append(d)
        return dirs

    def path(self, refpath, extra_search_dirs=None):
        """Find file in list of directories to search. Returns absolute path or raises FileNotFoundError."""
        search_dirs = []
        if extra_search_dirs:
            search_dirs.extend(extra_search_dirs)
        search_dirs.extend(self.dirlist)

        found = find_path(refpath, search_dirs)
        if found:
            return str(found[0])

        if os.path.isabs(os.path.expanduser(refpath)):
            raise FileNotFoundError(f"Absolute file '{refpath}' does not exist.")

        raise FileNotFoundError(
            f"Could not find '{refpath}' in search paths: {search_dirs}"
        )
