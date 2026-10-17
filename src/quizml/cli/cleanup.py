from pathlib import Path
from string import Template

from quizml.cli.config import peek_yaml_header
from quizml.cli.errorhandler import err_console
from quizml.exceptions import QuizMLConfigError


def get_cleanup_candidates(yaml_path, targets):
    """Return configured outputs and declared sidecars for one quiz file."""
    yaml_path = Path(yaml_path).expanduser().resolve()
    substitutions = {}
    header_data = peek_yaml_header(str(yaml_path))
    if isinstance(header_data, dict):
        for k, v in header_data.items():
            if isinstance(v, (str, int, float, bool)):
                substitutions[str(k)] = str(v)
    substitutions.update(
        {
            "inputbasename": yaml_path.stem,
            "inputstem": yaml_path.stem,
            "inputdir": str(yaml_path.parent),
        }
    )
    candidates = set()

    for target in targets:
        if not isinstance(target, dict):
            raise QuizMLConfigError("Each configured target must be a mapping.")
        output = target.get("out")
        if not isinstance(output, str) or not output:
            continue

        output = Template(output).safe_substitute(substitutions)
        output_path = Path(output).expanduser()
        if not output_path.is_absolute():
            output_path = yaml_path.parent / output_path
        output_path = output_path.resolve()
        candidates.add(output_path)

        extensions = target.get("clean_extensions", [])
        if not isinstance(extensions, list) or any(
            not isinstance(extension, str)
            or len(extension) < 2
            or not extension.startswith(".")
            or "/" in extension
            or "\\" in extension
            or any(char in extension for char in "*?[]")
            for extension in extensions
        ):
            name = target.get("name", "<unnamed>")
            raise QuizMLConfigError(
                f"Target '{name}' clean_extensions must be a list of file suffixes."
            )

        output_suffix = output_path.suffix
        output_stem = (
            output_path.name[: -len(output_suffix)]
            if output_suffix
            else output_path.name
        )
        for extension in extensions:
            candidates.add(output_path.with_name(f"{output_stem}{extension}"))

    return candidates


def _quiz_files(directory_path, target_stems, recursive=False):
    directory = Path(directory_path)
    if target_stems:
        return [directory / f"{stem}.yaml" for stem in set(target_stems)]
    if not recursive:
        return sorted(
            path
            for path in directory.iterdir()
            if path.is_file() and path.suffix in (".yaml", ".yml")
        )

    skipped_dirs = {"_quizml", "quizml-templates"}
    found = []

    def _walk(curr):
        for entry in sorted(curr.iterdir()):
            if entry.is_dir():
                if entry.name.startswith(".") or entry.name in skipped_dirs:
                    continue
                _walk(entry)
            elif entry.is_file() and entry.suffix in (".yaml", ".yml"):
                found.append(entry)

    _walk(directory)
    return found


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
    quiz_files = _quiz_files(dir_path, target_stems, recursive=recursive)
    if not quiet:
        err_console.print(f"Found {len(quiz_files)} YAML files to check.")

    candidates = set()
    for yaml_path in quiz_files:
        candidates.update(get_cleanup_candidates(yaml_path, targets))
    # A bad output configuration must never make clean remove a quiz source.
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
