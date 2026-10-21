import functools
import hashlib
import json
import logging
import shutil
import subprocess
from pathlib import Path

import platformdirs

CACHE_DIR = platformdirs.user_cache_dir("quizml")


def get_cache_dir():
    """Returns the cache directory, creating it if it doesn't exist."""
    Path(CACHE_DIR).mkdir(parents=True, exist_ok=True)
    logging.debug(f"Cache dir: {CACHE_DIR}")
    return Path(CACHE_DIR)


def get_cache_size():
    """Returns the total size in bytes of files in the cache directory."""
    cache_dir = Path(CACHE_DIR)
    if not cache_dir.is_dir():
        return 0
    return sum(path.stat().st_size for path in cache_dir.rglob("*") if path.is_file())


def clear_cache():
    """Remove the shared cache directory and return its previous size."""
    size = get_cache_size()
    try:
        shutil.rmtree(CACHE_DIR)
    except FileNotFoundError:
        pass
    return size


@functools.cache
def _tool_version(name):
    executable = shutil.which(name)
    if executable is None:
        return "not found"
    try:
        process = subprocess.run(
            [executable, "--version"],
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return f"unknown ({executable})"
    output = process.stdout or process.stderr
    first_line = next(
        (line.strip() for line in output.splitlines() if line.strip()), ""
    )
    return f"{executable}: {first_line or process.returncode}"


def renderer_tool_versions(backend):
    """Return the external tools whose versions can affect a renderer's output."""
    if backend == "MathML":
        try:
            import latex2mathml

            return {"latex2mathml": getattr(latex2mathml, "__version__", "installed")}
        except ImportError:
            return {"latex2mathml": "not found"}

    tools = {
        "PNG": ("pdflatex", "gs"),
        "SVG": ("latex", "dvisvgm"),
        "SVG_PDF": ("rsvg-convert", "inkscape"),
    }.get(backend, ())
    return {tool: _tool_version(tool) for tool in tools}


def compute_hash(content, settings_str="", tool_versions=None):
    """Computes a SHA256 hash for the given content and settings."""
    m = hashlib.sha256()
    m.update(content.encode("utf-8"))
    m.update(settings_str.encode("utf-8"))
    if tool_versions:
        m.update(json.dumps(tool_versions, sort_keys=True).encode("utf-8"))
    return m.hexdigest()


def get_from_cache(key):
    """Retrieves data from cache if it exists."""
    cache_path = get_cache_dir() / f"{key}.json"

    if cache_path.exists():
        try:
            return json.loads(cache_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            logging.warning(f"Failed to read cache for {key}")
            return None
    return None


def save_to_cache(key, data):
    """Saves data to cache."""
    cache_path = get_cache_dir() / f"{key}.json"
    try:
        cache_path.write_text(json.dumps(data), encoding="utf-8")
    except OSError:
        logging.warning(f"Failed to write cache for {key}")
