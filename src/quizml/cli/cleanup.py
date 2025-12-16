import os
from pathlib import Path

from rich import print

def cleanup_yaml_files(directory_path="."):
    """
    Looks at all .yaml files in a directory and deletes any other files 
    that share the same base name (name without extension).

    Args:
        directory_path (str): The directory to scan. Defaults to the current directory.
    """
    
    # 1. Identify all base names of .yaml files
    yaml_basenames = set()
    
    print(f"Scanning directory: {os.path.abspath(directory_path)}")
    
    for path in Path(directory_path).iterdir():
        # Check if the path is a file and ends with .yaml
        if path.is_file() and path.suffix == '.yaml':
            # Store the name without the extension (the 'stem')
            yaml_basenames.add(path.stem)

    print(f"Found {len(yaml_basenames)} unique YAML base names to check.")

    # 2. Iterate again and delete non-YAML files with matching base names
    deleted_files_count = 0
    
    for path in Path(directory_path).iterdir():
        # Check if the file's base name is in our set AND it's not a .yaml file
        if path.is_file() and path.stem in yaml_basenames and path.suffix != '.yaml':
            print(f"-> Deleting file: {path.name}")
            try:
                # Use os.remove for deletion
                os.remove(path)
                deleted_files_count += 1
            except OSError as e:
                print(f"Error deleting file {path.name}: {e}")
                
    print("-" * 30)
    print(f"Cleanup complete. Total files deleted: {deleted_files_count}")

