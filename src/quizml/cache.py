
import os
import hashlib
import appdirs
import json
import logging
from pathlib import Path
import functools

CACHE_DIR = appdirs.user_cache_dir("quizml")

@functools.lru_cache(maxsize=1)
def get_cache_dir():
    """Returns the cache directory, creating it if it doesn't exist."""
    os.makedirs(CACHE_DIR, exist_ok=True)
    logging.debug(f"Cache dir: {CACHE_DIR}")
    return Path(CACHE_DIR)

def compute_hash(content, settings_str=""):
    """Computes a SHA256 hash for the given content and settings."""
    m = hashlib.sha256()
    m.update(content.encode('utf-8'))
    m.update(settings_str.encode('utf-8'))
    return m.hexdigest()

def get_from_cache(key):
    """Retrieves data from cache if it exists."""
    cache_path = get_cache_dir() / f"{key}.json"
    
    if cache_path.exists():
        try:
            return json.loads(cache_path.read_text())
        except (json.JSONDecodeError, OSError):
            logging.warning(f"Failed to read cache for {key}")
            return None
    return None

def save_to_cache(key, data):
    """Saves data to cache."""
    cache_path = get_cache_dir() / f"{key}.json"
    try:
        cache_path.write_text(json.dumps(data))
    except OSError:
        logging.warning(f"Failed to write cache for {key}")

def clear_cache():
    """Clears the cache directory."""
    import shutil
    shutil.rmtree(CACHE_DIR, ignore_errors=True)
