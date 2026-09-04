from pathlib import Path

from rich import print

# Suffixes relative to the YAML base stem (e.g. "exam" -> "exam" + suffix)
KNOWN_TARGET_SUFFIXES = {
    ".txt",
    ".html",
    ".tex",
    ".solutions.tex",
    ".pdf",
    ".solutions.pdf",
    ".docx",
    ".csv",
}

# Intermediate LaTeX build artifact extensions
LATEX_ARTIFACT_EXTENSIONS = {
    ".aux",
    ".log",
    ".out",
    ".fls",
    ".fdb_latexmk",
    ".synctex.gz",
    ".toc",
    ".nav",
    ".snm",
    ".vrb",
    ".bbl",
    ".blg",
    ".dvi",
    ".xdv",
}


def get_cleanup_candidates(stem):
    """Returns the set of filenames that are known build artifacts or targets for a given YAML stem."""
    candidates = {f"{stem}{s}" for s in KNOWN_TARGET_SUFFIXES}
    for base in (stem, f"{stem}.solutions"):
        for ext in LATEX_ARTIFACT_EXTENSIONS:
            candidates.add(f"{base}{ext}")
    return candidates


def cleanup_yaml_files(directory_path=".", dry_run=False, target_stems=None):
    """
    Looks at all .yaml files in a directory (or specific target_stems) and deletes
    generated targets and LaTeX build artifacts matching their base names.
    Non-target files (like .py, .md, .png, etc.) are never deleted.

    Args:
        directory_path (str): The directory to scan. Defaults to the current directory.
        dry_run (bool): If True, only prints files that would be deleted without deleting them.
        target_stems (iterable): Optional set/list of specific YAML stems to clean up.
    """
    dir_path = Path(directory_path)
    if not dir_path.is_dir():
        print(f"Directory not found: {directory_path}")
        return 0

    print(f"Scanning directory: {dir_path.resolve()}")

    # 1. Identify base names of .yaml files to clean up
    if target_stems:
        yaml_stems = set(target_stems)
    else:
        yaml_stems = {
            p.stem for p in dir_path.iterdir() if p.is_file() and p.suffix in (".yaml", ".yml")
        }
    print(f"Found {len(yaml_stems)} unique YAML stems to check.")

    # 2. Build set of allowed filenames to clean up
    allowed_to_delete = set()
    for stem in yaml_stems:
        allowed_to_delete.update(get_cleanup_candidates(stem))

    # 3. Check directory for matches and delete safely
    deleted_files_count = 0
    for path in dir_path.iterdir():
        if path.is_file() and path.name in allowed_to_delete:
            if dry_run:
                print(f"-> [Dry-run] Would delete: {path.name}")
            else:
                print(f"-> Deleting file: {path.name}")
                try:
                    path.unlink()
                    deleted_files_count += 1
                except OSError as e:
                    print(f"Error deleting file {path.name}: {e}")

    print("-" * 30)
    action = "Would delete" if dry_run else "Total files deleted"
    print(f"Cleanup complete. {action}: {deleted_files_count}")
    return deleted_files_count
