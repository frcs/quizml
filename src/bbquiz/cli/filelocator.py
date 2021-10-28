import os
import appdirs
import pathlib

class FileLocator:
    """
    Config file and templates are defined as a relative path, and searched in:
    1. the local directory from which BBQuiz is called 
    2. the default application config dir 
    3. the install package templates dir
    """

    def __init__(self):
        """
        sets up default directories to search
        """
        
        pkg_template_dir = os.path.join(os.path.dirname(__file__), '../templates')
        app_dir = appdirs.user_config_dir(appname="bbquiz", appauthor='frcs')
        user_config_dir = os.path.join(app_dir, 'templates')
        self.dirlist = [ os.getcwd(), user_config_dir, pkg_template_dir ]

    def path(self, refpath):
        """
        finds file in list of directories to search. returns None
        """
        
        if os.path.isabs(refpath):
            if os.path.exists(refpath):
                return path
        else:
            for d in self.dirlist:
                abspath = os.path.realpath(
                    os.path.expanduser(os.path.join(d, refpath)))
                if os.path.exists(abspath):
                    return abspath
        return FileNotFoundError(f"{refpath} was not found")
    
locate = FileLocator()
