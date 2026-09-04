"""Configuration and template file resolution across local, user, and package paths."""

import os
from pathlib import Path

import appdirs


class FileLocator:
    """Config file and templates are defined as relative paths, and searched in:

    1. the local directory from which QuizML is called
    2. a `quizml-templates` subdirectory of the local directory
    3. the default application user config dir (~/.config/quizml/templates)
    4. the install package templates dir
    """

    def __init__(self):
        self.pkg_template_dir = str(Path(__file__).parent / "templates")
        self.app_dir = appdirs.user_config_dir(appname="quizml", appauthor="frcs")
        self.user_template_dir = os.path.join(self.app_dir, "templates")

    @property
    def cw_dir(self):
        return os.getcwd()

    @property
    def local_template_dir(self):
        return os.path.join(self.cw_dir, "quizml-templates")

    @property
    def dirlist(self):
        return [
            self.cw_dir,
            self.local_template_dir,
            self.user_template_dir,
            self.pkg_template_dir,
        ]

    def path(self, refpath, extra_search_dirs=None):
        """Finds file in list of directories to search.

        Returns absolute path or raises FileNotFoundError.
        """
        if os.path.isabs(refpath):
            if os.path.exists(refpath):
                return refpath
            raise FileNotFoundError(f"Absolute file '{refpath}' does not exist.")

        search_dirs = []
        if extra_search_dirs:
            search_dirs.extend(extra_search_dirs)
        search_dirs.extend(self.dirlist)

        for d in search_dirs:
            abspath = os.path.realpath(os.path.expanduser(os.path.join(d, refpath)))
            if os.path.exists(abspath):
                return abspath

        raise FileNotFoundError(
            f"Could not find '{refpath}' in search paths: {search_dirs}"
        )


locate = FileLocator()
