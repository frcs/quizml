import os
import appdirs
import pathlib
import shutil

def init_local():

    pkg_template_dir = os.path.join(os.path.dirname(__file__), '../templates')
    cw_dir = os.getcwd()
    local_confdir =  os.path.join(cw_dir, 'bbquiz_conf')
    
    # Check if the source directory exists
    if not os.path.isdir(pkg_template_dir):
        print(f"Error: Template directory not found at {pkg_template_dir}")
    else:
        # Create the local_confdir directory and copy contents
        try:
            # shutil.copytree will:
            # - Create the destination directory (local_confdir)
            # - Recursively copy all files and subdirectories from pkg_template_dir into it
            # - Use dirs_exist_ok=True to avoid an error if local_confdir already exists 
            #   (and instead, merge the contents)
            shutil.copytree(pkg_template_dir, local_confdir, dirs_exist_ok=True)
            print(f"Successfully copied contents from {pkg_template_dir} to {local_confdir}")

        except Exception as e:
            print(f"An error occurred during copy: {e}")

            
def init_user():
    pkg_template_dir = os.path.join(os.path.dirname(__file__), '../templates')
    app_dir = appdirs.user_config_dir(appname="bbquiz", appauthor='frcs')
    user_config_dir = os.path.join(app_dir, 'templates')
    
    # Check if the source directory exists
    if not os.path.isdir(pkg_template_dir):
        print(f"Error: Template directory not found at {pkg_template_dir}")
    else:
        # Create the local_confdir directory and copy contents
        try:
            # shutil.copytree will:
            # - Create the destination directory (local_confdir)
            # - Recursively copy all files and subdirectories from pkg_template_dir into it
            # - Use dirs_exist_ok=True to avoid an error if local_confdir already exists 
            #   (and instead, merge the contents)
            shutil.copytree(pkg_template_dir, user_config_dir, dirs_exist_ok=True)
            print(f"Successfully copied contents from {pkg_template_dir} to {user_config_dir}")

        except Exception as e:
            print(f"An error occurred during copy: {e}")


