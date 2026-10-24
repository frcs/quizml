"""CLI adapter for pinning quiz metadata, question IDs, and includes."""

import sys
from pathlib import Path
from types import SimpleNamespace

from quizml.cli.config import get_config
from quizml.cli.errorhandler import err_console
from quizml.exceptions import QuizMLConfigError, QuizMLError
from quizml.yaml.pin import (
    default_version_constraint,
    generate_question_id,
    parse_version_tuple,
    pin_yaml_text,
)

_default_version_constraint = default_version_constraint
_generate_question_id = generate_question_id
_parse_version_tuple = parse_version_tuple


def run_pin(args):
    source = args.file
    if source == "-":
        raw_text = sys.stdin.read()
        source_label = "<stdin>"
        base_dir = Path.cwd().resolve()
        yaml_for_cfg = None
    else:
        source_path = Path(source).expanduser()
        if not source_path.is_file():
            raise QuizMLConfigError(f"File not found: {source_path}")
        source_path = source_path.resolve()
        raw_text = source_path.read_text(encoding="utf-8")
        source_label = str(source_path)
        base_dir = source_path.parent
        yaml_for_cfg = str(source_path)

    output = getattr(args, "output", None)
    if output is None:
        output = "-" if source == "-" else str(source_path)

    if (
        output != "-"
        and source != "-"
        and Path(output).expanduser().resolve() != source_path
        and Path(output).expanduser().exists()
        and not getattr(args, "force", False)
    ):
        raise QuizMLConfigError(
            f"Refusing to overwrite existing file {output} (use --force)."
        )

    config = get_config(
        SimpleNamespace(
            config=getattr(args, "config", None),
            yaml_filename=yaml_for_cfg,
        )
    )

    out_dir = (
        base_dir
        if output == "-"
        else Path(output).expanduser().resolve().parent
    )

    cli_targets = getattr(args, "target", None)
    default_targets = cli_targets or config.get("default_targets")

    formatted = pin_yaml_text(
        raw_text,
        base_dir=base_dir,
        source_label=source_label,
        out_dir=out_dir,
        force=getattr(args, "force", False),
        default_targets=default_targets,
        schema_path=config.get("schema_path"),
        freeze_includes=getattr(args, "freeze_includes", False),
        seed=getattr(args, "seed", None),
        add_ids=getattr(args, "add_ids", False),
        initial_stack=(source_path,) if source != "-" else (),
    )

    if output == "-":
        sys.stdout.write(formatted)
    else:
        out_path = Path(output).expanduser()
        try:
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(formatted, encoding="utf-8")
        except OSError as err:
            raise QuizMLError(f"Could not write {out_path}: {err}") from err
        if not getattr(args, "quiet", False):
            err_console.print(f"Pinned metadata in {out_path}")
    return True


__all__ = [
    "_default_version_constraint",
    "_generate_question_id",
    "_parse_version_tuple",
    "run_pin",
]
