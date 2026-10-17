import os

import platformdirs

from quizml.paths import find_path


class FileLocator:
    """
    Config file and templates are defined as a relative path, and searched in:
    1. the local directory from which QuizML is called
    2. a `quizml-templates` subdirectory of the local directory
    2. the default application config dir
    3. the install package templates dir
    """

    def __init__(self, cwd=None, base_dir=None):
        """
        sets up default directories to search
        """
        self.pkg_template_dir = os.path.join(os.path.dirname(__file__), "../templates")
        self.app_dir = platformdirs.user_config_dir(appname="quizml", appauthor="frcs")
        self.user_template_dir = os.path.join(self.app_dir, "templates")
        self._cwd = os.path.abspath(cwd or os.getcwd())
        self._base_dir = os.path.abspath(base_dir) if base_dir else None

    @property
    def cw_dir(self):
        return self._cwd

    @property
    def local_template_dir(self):
        return os.path.join(self.cw_dir, "quizml-templates")

    @property
    def dirlist(self):
        dirs = []
        if self._base_dir:
            dirs.append(self._base_dir)
            dirs.append(os.path.join(self._base_dir, "quizml-templates"))
        for d in (
            self.cw_dir,
            self.local_template_dir,
            self.user_template_dir,
            self.pkg_template_dir,
        ):
            if d not in dirs:
                dirs.append(d)
        return dirs

    def path(self, refpath, extra_search_dirs=None):
        """
        finds file in list of directories to search. returns absolute path or raises FileNotFoundError.
        """
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
