"""CLI adapter for expanding and sampling question-bank includes."""

import os
from pathlib import Path

from quizml.exceptions import QuizMLError
from quizml.yaml.includes import (
    _comment_tokens,
    _sample_questions,
    expand_roundtrip_includes,
)
from quizml.yaml.parser import (
    extract_figure_paths,
    parse_roundtrip_yaml_text,
    read_roundtrip_yaml,
)

_parse_yaml_text = parse_roundtrip_yaml_text
_read_yaml = read_roundtrip_yaml
_figure_paths = extract_figure_paths
_expand = expand_roundtrip_includes


def run_sample(args):
    import sys

    file_arg = getattr(args, "file", "-") or "-"
    output_arg = getattr(args, "output", "-") or "-"

    if file_arg == "-":
        source = None
        source_dir = Path.cwd().resolve()
        source_label = "<stdin>"
    else:
        source = Path(file_arg).expanduser().resolve()
        source_dir = source.parent
        source_label = source

    if output_arg == "-":
        output = None
        output_dir = Path.cwd().resolve()
    else:
        output = Path(output_arg).expanduser().resolve()
        output_dir = output.parent
        if source is not None and source == output:
            raise QuizMLError(
                "Sample output must be different from the meta YAML input"
            )
        if output.exists() and not args.force:
            raise QuizMLError(
                f"Output already exists: {output}. Use --force to replace it."
            )

    if source is None:
        yaml, docs, q_index = parse_roundtrip_yaml_text(sys.stdin.read(), source_label)
        initial_stack = ()
    else:
        yaml, docs, q_index = read_roundtrip_yaml(source)
        initial_stack = (source,)

    if q_index is None:
        raise QuizMLError(f"No questions found in {source_label}")
    figure_dirs = list(
        extract_figure_paths(docs[0], source_dir) if q_index == 1 else []
    )
    docs[q_index] = expand_roundtrip_includes(
        docs[q_index],
        source_dir,
        inherited_seed=args.seed,
        stack=initial_stack,
        figure_dirs=figure_dirs,
    )
    if figure_dirs:
        rel_dirs = list(
            dict.fromkeys(os.path.relpath(path, output_dir) for path in figure_dirs)
        )
        if q_index == 0:
            docs.insert(0, {"_figures_path": rel_dirs})
        else:
            docs[0]["_figures_path"] = rel_dirs

    if output is None:
        yaml.dump_all(docs, sys.stdout)
    else:
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("w", encoding="utf-8") as stream:
            yaml.dump_all(docs, stream)
    return True


__all__ = [
    "_comment_tokens",
    "_expand",
    "_figure_paths",
    "_parse_yaml_text",
    "_read_yaml",
    "_sample_questions",
    "run_sample",
]
