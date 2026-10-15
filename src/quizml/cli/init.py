import os
import shutil

import platformdirs

from ..exceptions import QuizMLConfigError


def _copy_templates(dest_dir):
    pkg_template_dir = os.path.join(os.path.dirname(__file__), "../templates")
    if not os.path.isdir(pkg_template_dir):
        raise QuizMLConfigError(f"Template directory not found at {pkg_template_dir}")

    try:
        shutil.copytree(pkg_template_dir, dest_dir, dirs_exist_ok=True)
        print(f"Successfully copied contents from {pkg_template_dir} to {dest_dir}")
        return True
    except OSError as e:
        raise QuizMLConfigError(f"Could not copy templates to {dest_dir}: {e}") from e


def init_local():
    local_template_dir = os.path.join(os.getcwd(), "quizml-templates")
    return _copy_templates(local_template_dir)


def init_user():
    app_dir = platformdirs.user_config_dir(appname="quizml", appauthor="frcs")
    user_template_dir = os.path.join(app_dir, "templates")
    return _copy_templates(user_template_dir)
