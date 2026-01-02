import os
import appdirs
import pathlib

class FileLocator:
    """
    Config file and templates are defined as a relative path, and searched in:
    1. the local directory from which QuizML is called 
    2. a `quizml-templates` subdirectory of the local directory
    2. the default application config dir 
    3. the install package templates dir
    """

    def __init__(self):
        """
        sets up default directories to search
        """
        
        self.pkg_template_dir = os.path.join(os.path.dirname(__file__), '../templates')
        self.app_dir = appdirs.user_config_dir(appname="quizml", appauthor='frcs')
        self.user_template_dir = os.path.join(self.app_dir, 'templates')
        self.cw_dir = os.getcwd()
        self.local_template_dir =  os.path.join(self.cw_dir, 'quizml-templates')
        self.dirlist = [ self.cw_dir, self.local_template_dir, self.user_template_dir, self.pkg_template_dir ]

    def path(self, refpath):
        """
        finds file in list of directories to search. returns None
        """
        
        if os.path.isabs(refpath):
            if os.path.exists(refpath):
                return refpath
        else:
            for d in self.dirlist:
                abspath = os.path.realpath(
                    os.path.expanduser(os.path.join(d, refpath)))
                if os.path.exists(abspath):
                    return abspath
        raise FileNotFoundError
    
locate = FileLocator()
