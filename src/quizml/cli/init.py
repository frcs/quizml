import os
import appdirs
import pathlib
import shutil

def init_local():

    pkg_template_dir = os.path.join(os.path.dirname(__file__), '../templates')
    cw_dir = os.getcwd()
    local_template_dir =  os.path.join(cw_dir, 'quizml-templates')
    
    # Check if the source directory exists
    if not os.path.isdir(pkg_template_dir):
        print(f"Error: Template directory not found at {pkg_template_dir}")
    else:
        # Create the local_template_dir directory and copy contents
        try:
            # shutil.copytree will:
            # - Create the destination directory (local_template_dir)
            # - Recursively copy all files and subdirectories from pkg_template_dir into it
            # - Use dirs_exist_ok=True to avoid an error if local_template_dir already exists 
            #   (and instead, merge the contents)
            shutil.copytree(pkg_template_dir, local_template_dir, dirs_exist_ok=True)
            print(f"Successfully copied contents from {pkg_template_dir} to {local_template_dir}")

        except Exception as e:
            print(f"An error occurred during copy: {e}")

            
def init_user():
    pkg_template_dir = os.path.join(os.path.dirname(__file__), '../templates')
    app_dir = appdirs.user_config_dir(appname="quizml", appauthor='frcs')
    user_template_dir = os.path.join(app_dir, 'templates')
    
    # Check if the source directory exists
    if not os.path.isdir(pkg_template_dir):
        print(f"Error: Template directory not found at {pkg_template_dir}")
    else:
        # Create the local_template_dir directory and copy contents
        try:
            # shutil.copytree will:
            # - Create the destination directory (local_template_dir)
            # - Recursively copy all files and subdirectories from pkg_template_dir into it
            # - Use dirs_exist_ok=True to avoid an error if local_template_dir already exists 
            #   (and instead, merge the contents)
            shutil.copytree(pkg_template_dir, user_template_dir, dirs_exist_ok=True)
            print(f"Successfully copied contents from {pkg_template_dir} to {user_template_dir}")

        except Exception as e:
            print(f"An error occurred during copy: {e}")


