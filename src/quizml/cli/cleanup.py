"""CLI command handler for cleaning up generated targets and build artifacts."""

from pathlib import Path

from rich import print

from quizml.tools.cleanup import (
    KNOWN_TARGET_SUFFIXES,
    LATEX_ARTIFACT_EXTENSIONS,
    find_cleanup_files,
    get_cleanup_candidates,
)


def cleanup_yaml_files(directory_path=".", dry_run=False, target_stems=None):
    """CLI runner for cleanup: scans directory, reports to terminal, and deletes artifacts."""
    dir_path = Path(directory_path).resolve()
    if not dir_path.is_dir():
        print(f"Directory not found: {directory_path}")
        return 0

    print(f"Scanning directory: {dir_path}")

    files = find_cleanup_files(dir_path, target_stems=target_stems)
    action = "Would delete" if dry_run else "Deleting file"

    deleted_count = 0
    for f in files:
        if dry_run:
            print(f"-> [Dry-run] Would delete: {f.name}")
        else:
            print(f"-> {action}: {f.name}")
            try:
                f.unlink()
                deleted_count += 1
            except OSError as e:
                print(f"Error deleting file {f.name}: {e}")

    print("-" * 30)
    summary_label = "Would delete" if dry_run else "Total files deleted"
    count = len(files) if dry_run else deleted_count
    print(f"Cleanup complete. {summary_label}: {count}")
    return count


__all__ = [
    "cleanup_yaml_files",
    "get_cleanup_candidates",
    "KNOWN_TARGET_SUFFIXES",
    "LATEX_ARTIFACT_EXTENSIONS",
]
