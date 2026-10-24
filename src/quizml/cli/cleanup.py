"""CLI adapter for artifact cleanup."""

from pathlib import Path

from quizml.build.cleanup import find_quiz_files, get_cleanup_candidates
from quizml.cli.errorhandler import err_console
from quizml.exceptions import QuizMLConfigError

_quiz_files = find_quiz_files


def cleanup_yaml_files(
    directory_path=".",
    dry_run=False,
    target_stems=None,
    targets=None,
    quiet=False,
    recursive=False,
):
    """Clean configured outputs and declared sidecars for quizzes in a directory."""
    dir_path = Path(directory_path).expanduser()
    if not dir_path.is_dir():
        raise QuizMLConfigError(f"Directory not found: {directory_path}")
    if targets is None:
        raise QuizMLConfigError("Target configuration is required for cleanup.")

    if not quiet:
        err_console.print(f"Scanning directory: {dir_path.resolve()}")
    quiz_files = find_quiz_files(dir_path, target_stems, recursive=recursive)
    if not quiet:
        err_console.print(f"Found {len(quiz_files)} YAML files to check.")

    candidates = set()
    for yaml_path in quiz_files:
        candidates.update(get_cleanup_candidates(yaml_path, targets))
    candidates = {
        path for path in candidates if path.suffix.lower() not in {".yaml", ".yml"}
    }

    deleted_files_count = 0
    errors = []
    for path in sorted(candidates, key=str):
        if path.is_file():
            if dry_run:
                if not quiet:
                    err_console.print(f"-> [Dry-run] Would delete: {path}")
            else:
                if not quiet:
                    err_console.print(f"-> Deleting file: {path}")
                try:
                    path.unlink()
                    deleted_files_count += 1
                except OSError as error:
                    errors.append(f"Could not delete {path}: {error}")

    if not quiet:
        err_console.print("-" * 30)
        action = "Would delete" if dry_run else "Total files deleted"
        err_console.print(f"Cleanup complete. {action}: {deleted_files_count}")
    if errors:
        raise QuizMLConfigError("\n".join(errors))
    return deleted_files_count
