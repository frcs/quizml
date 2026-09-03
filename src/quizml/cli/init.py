import os
import shutil

import appdirs


def _copy_templates(dest_dir):
    pkg_template_dir = os.path.join(os.path.dirname(__file__), "../templates")
    if not os.path.isdir(pkg_template_dir):
        print(f"Error: Template directory not found at {pkg_template_dir}")
        return

    try:
        shutil.copytree(pkg_template_dir, dest_dir, dirs_exist_ok=True)
        print(f"Successfully copied contents from {pkg_template_dir} to {dest_dir}")
    except Exception as e:
        print(f"An error occurred during copy: {e}")


def init_local():
    local_template_dir = os.path.join(os.getcwd(), "quizml-templates")
    _copy_templates(local_template_dir)


def init_user():
    app_dir = appdirs.user_config_dir(appname="quizml", appauthor="frcs")
    user_template_dir = os.path.join(app_dir, "templates")
    _copy_templates(user_template_dir)
