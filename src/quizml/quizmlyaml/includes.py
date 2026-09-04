"""Recursive resolution of '_include' directives in QuizML question lists."""

import os
from pathlib import Path

from quizml.exceptions import QuizMLYamlSyntaxError
from quizml.quizmlyaml.parser import parse_yaml_docs


def count_included_questions(
    item: dict, base_dir: Path, visited: set[Path] | None = None
) -> int:
    """Calculates the number of questions contributed by an _include item.

    Recursively counts nested _include items.
    Falls back gracefully to 1 if the file cannot be accessed.
    """
    if visited is None:
        visited = set()

    inc_file = str(item.get("_include", "")).strip()
    if not inc_file:
        return 0

    inc_path = (
        Path(inc_file).resolve()
        if os.path.isabs(inc_file)
        else (base_dir / inc_file).resolve()
    )

    if not inc_path.is_file() or inc_path in visited:
        return 1

    try:
        inc_text = inc_path.read_text(encoding="utf-8")
        _, sub_questions = parse_yaml_docs(inc_text, filename=str(inc_path))
    except Exception:
        return 1

    if not isinstance(sub_questions, list):
        return 0

    new_visited = visited | {inc_path}
    total = 0
    for q in sub_questions:
        if isinstance(q, dict) and "_include" in q:
            total += count_included_questions(q, inc_path.parent, new_visited)
        else:
            total += 1

    return total


def resolve_includes(
    questions_data: list,
    base_dir: Path,
    root_dir: Path,
    visited: set[Path] | None = None,
    accumulated_figure_dirs: list[str] | None = None,
) -> list:
    """Recursively resolves '- _include: filename.yaml' directives in the questions list.

    Detects circular includes using the visited set.
    Accumulates figure search directories relative to root_dir.
    """
    if visited is None:
        visited = set()
    if accumulated_figure_dirs is None:
        accumulated_figure_dirs = []

    resolved = []
    for item in questions_data:
        if isinstance(item, dict) and "include" in item and "_include" not in item:
            raise QuizMLYamlSyntaxError(
                "Unknown directive 'include'. Did you mean '_include'?"
            )
        if isinstance(item, dict) and "_include" in item:
            inc_file = str(item["_include"]).strip()
            inc_path = (
                Path(inc_file).resolve()
                if os.path.isabs(inc_file)
                else (base_dir / inc_file).resolve()
            )

            if not inc_path.is_file():
                raise QuizMLYamlSyntaxError(
                    f"Included YAML file not found: '{inc_file}' (resolved to '{inc_path}')"
                )

            if inc_path in visited:
                raise QuizMLYamlSyntaxError(
                    f"Circular include detected: '{inc_path}' is already in the inclusion chain."
                )

            try:
                inc_text = inc_path.read_text(encoding="utf-8")
            except Exception as err:
                raise QuizMLYamlSyntaxError(
                    f"Error reading included file '{inc_path}': {err}"
                ) from err

            sub_header, sub_questions = parse_yaml_docs(
                inc_text, filename=str(inc_path)
            )

            # Accumulate figure paths from sub-file header
            if sub_header:
                sub_figures = sub_header.get("_figures_path", [])
                if isinstance(sub_figures, str):
                    sub_figures = [sub_figures]
                elif not isinstance(sub_figures, list):
                    sub_figures = []
                for p in sub_figures:
                    p_str = str(p).strip()
                    sub_fig_path = (
                        Path(p_str).resolve()
                        if os.path.isabs(p_str)
                        else (inc_path.parent / p_str).resolve()
                    )
                    rel_fig_dir = os.path.relpath(sub_fig_path, root_dir)
                    if rel_fig_dir not in accumulated_figure_dirs:
                        accumulated_figure_dirs.append(rel_fig_dir)

            if inc_path.parent != root_dir:
                rel_inc_dir = os.path.relpath(inc_path.parent, root_dir)
                if rel_inc_dir not in accumulated_figure_dirs:
                    accumulated_figure_dirs.append(rel_inc_dir)

            # Recursively resolve nested includes
            new_visited = visited | {inc_path}
            sub_questions = resolve_includes(
                sub_questions,
                inc_path.parent,
                root_dir,
                new_visited,
                accumulated_figure_dirs,
            )

            resolved.extend(sub_questions)
        else:
            resolved.append(item)

    return resolved
