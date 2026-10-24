"""Output and sidecar artifact cleanup discovery for QuizML."""

from pathlib import Path
from string import Template

from quizml.build.config import build_target_substitutions
from quizml.exceptions import QuizMLConfigError
from quizml.yaml.parser import peek_yaml_header


def get_cleanup_candidates(yaml_path, targets):
    """Return configured outputs and declared sidecars for one quiz file."""
    yaml_path = Path(yaml_path).expanduser().resolve()
    header_data = peek_yaml_header(str(yaml_path))
    substitutions, _, _ = build_target_substitutions(str(yaml_path), header_data)
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


def find_quiz_files(directory_path, target_stems=None, recursive=False):
    """Find YAML quiz files in a directory."""
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
