"""Unified question-bank ``_include``, ``select``, and deterministic sampling engine.

Supports two distinct expansion modes:
1. **Compilation mode** (``resolve_includes``): Used by ``quizml.yaml.loads()`` when
   building outputs. Validates each included file's questions with source line
   numbers before flattening, collects relative ``_figures_path`` directories,
   and rejects unmaterialized random sampling options (``count`` / ``seed``).
2. **Round-trip mode** (``expand_roundtrip_includes``): Used by ``quizml sample``
   and ``quizml pin --freeze-includes``. Preserves ``ruamel.yaml`` ``CommentToken``
   attachments and materializes ``select`` and deterministic ``count``/``seed``
   sampling into a static YAML sequence.
"""

import copy
import os
import random
from pathlib import Path
from typing import Any

from ruamel.yaml.comments import CommentedSeq
from ruamel.yaml.tokens import CommentToken

from quizml.exceptions import QuizMLError, QuizMLYamlSyntaxError
from quizml.paths import find_path
from quizml.yaml.parser import (
    extract_figure_paths,
    read_question_file,
    read_roundtrip_yaml,
)
from quizml.yaml.schema import validate_header, validate_source_questions


def resolve_include_path(filename: str | Path, base_dir: Path) -> Path:
    """Resolve an ``_include`` path relative to ``base_dir`` or search paths."""
    found = find_path(str(filename), [base_dir])
    if found:
        return found[0]
    requested = Path(filename).expanduser()
    if not requested.is_absolute():
        requested = Path(base_dir) / requested
    return Path(os.path.realpath(requested))


def normalize_select_list(
    select_spec: Any,
    error_cls: type[Exception] = QuizMLYamlSyntaxError,
) -> list[str]:
    """Normalize a ``select`` spec into a list of non-empty selector strings."""
    if isinstance(select_spec, list):
        return [str(x).strip() for x in select_spec if str(x).strip()]
    if isinstance(select_spec, (str, int)):
        return [s.strip() for s in str(select_spec).split(",") if s.strip()]
    raise error_cls(
        "Include 'select' must be a list or comma-separated string of "
        "question IDs or 1-based indices."
    )


def resolve_select_indices(
    questions: list[Any],
    select_spec: Any,
    source_label: str | Path,
    error_cls: type[Exception] = QuizMLYamlSyntaxError,
) -> list[int]:
    """Return 0-based indices matching ``select_spec`` (by ID or 1-based index)."""
    selectors = normalize_select_list(select_spec, error_cls=error_cls)
    by_id: dict[str, int] = {
        str(q["id"]).strip(): idx
        for idx, q in enumerate(questions)
        if isinstance(q, dict) and q.get("id")
    }
    chosen_indices: list[int] = []
    for sel in selectors:
        if sel in by_id:
            chosen_indices.append(by_id[sel])
        elif sel.isdigit():
            pos = int(sel)
            if 1 <= pos <= len(questions):
                chosen_indices.append(pos - 1)
            else:
                raise error_cls(
                    f"Include 'select' index {pos} is out of range "
                    f"(1..{len(questions)}) in '{source_label}'."
                )
        else:
            raise error_cls(
                f"Include 'select' ID '{sel}' not found in '{source_label}'."
            )
    return chosen_indices


def select_questions(
    questions: list[Any], select_spec: Any, source_label: str | Path
) -> list[Any]:
    """Return the subset of ``questions`` matching ``select_spec``."""
    indices = resolve_select_indices(
        questions, select_spec, source_label, error_cls=QuizMLYamlSyntaxError
    )
    return [questions[i] for i in indices]


def count_included_questions(
    item: dict[str, Any], base_dir: Path, visited: set[Path] | None = None
) -> int:
    """Count the number of questions contributed by an ``_include`` entry, recursively.

    Used by ``format_yaml_text`` to generate ``# <Q1>, <Q2>, ...`` range comments
    above ``_include`` directives without mutating or failing on partial files.
    """
    if visited is None:
        visited = set()

    inc_file = str(item.get("_include", "")).strip()
    if not inc_file:
        return 0

    inc_path = resolve_include_path(inc_file, base_dir)
    if not inc_path.is_file() or inc_path in visited:
        return 1

    try:
        _, sub_questions, _ = read_question_file(inc_path)
    except QuizMLYamlSyntaxError:
        return 1

    new_visited = visited | {inc_path}
    total = 0
    for q in sub_questions:
        if isinstance(q, dict) and "_include" in q:
            total += count_included_questions(q, inc_path.parent, new_visited)
        else:
            total += 1

    if "select" in item:
        try:
            selectors = normalize_select_list(item["select"])
            return min(len(selectors), total)
        except QuizMLYamlSyntaxError:
            return total
    if "count" in item:
        try:
            requested = int(item["count"])
        except (TypeError, ValueError):
            return total
        return min(max(requested, 0), total)
    return total


def _reject_include_sampling(item: dict[str, Any]) -> None:
    """Validate keys on an ``_include`` mapping during compilation.

    Random sampling directives (``count`` and ``seed``) must be materialized into
    a static quiz file via ``quizml sample`` before compiling outputs.
    """
    unknown = sorted(set(item) - {"_include", "count", "seed", "select"})
    if unknown:
        options = ", ".join(f"'{option}'" for option in unknown)
        raise QuizMLYamlSyntaxError(
            f"Unknown directive(s) in _include mapping: {options}."
        )
    if "select" in item and ("count" in item or "seed" in item):
        raise QuizMLYamlSyntaxError(
            "Cannot combine 'select' with 'count' or 'seed' in _include."
        )
    unsupported = sorted({"count", "seed"}.intersection(item))
    if unsupported:
        options = ", ".join(f"'{option}'" for option in unsupported)
        raise QuizMLYamlSyntaxError(
            f"Include sampling options {options} cannot be used while compiling. "
            "Run 'quizml sample' to create a static quiz file first."
        )


def resolve_includes(
    questions_data: list[Any],
    base_dir: Path,
    root_dir: Path,
    visited: set[Path] | None = None,
    accumulated_figure_dirs: list[str] | None = None,
    schema: dict[str, Any] | None = None,
    source_text: str = "",
    source_path: str = "<string>",
) -> list[Any]:
    """Recursively resolve ``- _include: filename.yaml`` directives for compilation."""
    if visited is None:
        visited = set()
    if accumulated_figure_dirs is None:
        accumulated_figure_dirs = []

    validate_source_questions(
        questions_data, schema, source_text=source_text, source_path=source_path
    )

    resolved: list[Any] = []
    for item in questions_data:
        if isinstance(item, dict) and "include" in item and "_include" not in item:
            raise QuizMLYamlSyntaxError(
                "Unknown directive 'include'. Did you mean '_include'?"
            )
        if isinstance(item, dict) and "_include" in item:
            _reject_include_sampling(item)
            inc_file = str(item["_include"]).strip()
            inc_path = resolve_include_path(inc_file, base_dir)

            if not inc_path.is_file():
                raise QuizMLYamlSyntaxError(
                    f"Included YAML file not found: '{inc_file}' "
                    f"(resolved to '{inc_path}')"
                )

            if inc_path in visited:
                raise QuizMLYamlSyntaxError(
                    f"Circular include detected: '{inc_path}' is already "
                    "in the inclusion chain."
                )

            sub_header, sub_questions, inc_text = read_question_file(inc_path)
            validate_header(sub_header, schema, inc_text, str(inc_path))

            # Collect figure search directories from the included file's header
            # as well as the included file's own parent directory.
            for sub_fig_path in extract_figure_paths(sub_header, inc_path.parent):
                rel_fig_dir = os.path.relpath(sub_fig_path, root_dir)
                if rel_fig_dir not in accumulated_figure_dirs:
                    accumulated_figure_dirs.append(rel_fig_dir)

            if inc_path.parent != root_dir:
                rel_inc_dir = os.path.relpath(inc_path.parent, root_dir)
                if rel_inc_dir not in accumulated_figure_dirs:
                    accumulated_figure_dirs.append(rel_inc_dir)

            new_visited = visited | {inc_path}
            sub_questions = resolve_includes(
                sub_questions,
                inc_path.parent,
                root_dir,
                new_visited,
                accumulated_figure_dirs,
                schema,
                inc_text,
                str(inc_path),
            )
            if "select" in item:
                sub_questions = select_questions(
                    sub_questions, item["select"], inc_file
                )

            resolved.extend(sub_questions)
        else:
            resolved.append(item)

    return resolved


# --- Comment-Preserving Round-Trip Include Expansion & Sampling ---


def _select_commented_seq(questions: list[Any], indices: list[int]) -> CommentedSeq:
    """Slice ``questions`` by ``indices`` while preserving ruamel item comments."""
    selected = CommentedSeq()
    comment = getattr(questions, "ca", None)
    for source_index in indices:
        selected.append(questions[source_index])
        if comment and source_index in comment.items:
            selected.ca.items[len(selected) - 1] = copy.deepcopy(
                comment.items[source_index]
            )
    return selected


def _sample_questions(questions: list[Any], count: int, seed: Any) -> CommentedSeq:
    """Deterministically sample ``count`` questions using ``seed``."""
    indices = random.Random(str(seed)).sample(range(len(questions)), count)
    return _select_commented_seq(questions, indices)


def _comment_tokens(data: Any) -> list[CommentToken]:
    """Extract all ``CommentToken`` instances attached to a ruamel node."""
    ca = getattr(data, "ca", None)
    if ca is None:
        return []
    tokens: list[CommentToken] = []

    def collect(value: Any) -> None:
        if isinstance(value, CommentToken):
            tokens.append(copy.deepcopy(value))
        elif isinstance(value, dict):
            for item in value.values():
                collect(item)
        elif isinstance(value, (list, tuple)):
            for item in value:
                collect(item)

    collect(ca.comment)
    collect(ca.end)
    collect(ca.items)
    return tokens


def _merge_comment_slots(
    existing: list[Any] | None, incoming: list[Any] | None, *, as_list: bool = True
) -> list[Any] | None:
    """Merge two ruamel.yaml 4-element comment slot lists.

    In ``ruamel.yaml``, ``seq.ca.items[idx]`` is a 4-element list:
    ``[pre_key, pre_item, post_key, post_item]``, where index ``1`` holds
    comments appearing before sequence item ``idx``.
    """
    if incoming is None:
        return existing
    if existing is None:
        return copy.deepcopy(incoming)

    for slot, value in enumerate(incoming):
        if value is None:
            continue
        if existing[slot] is None:
            existing[slot] = copy.deepcopy(value)
        elif as_list and isinstance(existing[slot], list):
            values = value if isinstance(value, list) else [value]
            existing[slot].extend(copy.deepcopy(values))
        else:
            existing[slot] = [existing[slot], copy.deepcopy(value)]
    return existing


def _append_commented_items(
    expanded: CommentedSeq,
    items: list[Any],
    comments: list[list[Any] | None] | None = None,
) -> None:
    """Append ``items`` to ``expanded`` and merge their associated ruamel comments."""
    start = len(expanded)
    expanded.extend(items)
    if not comments:
        return
    for offset, comment in enumerate(comments):
        if offset >= len(items) or comment is None:
            continue
        target_index = start + offset
        expanded.ca.items[target_index] = _merge_comment_slots(
            expanded.ca.items.get(target_index), comment, as_list=True
        )


def _apply_roundtrip_filter(
    bank_questions: CommentedSeq,
    directive: dict[str, Any],
    child_seed: str | None,
) -> CommentedSeq:
    """Apply ``select`` or ``count``/``seed`` filtering to an included question list."""
    if "select" in directive:
        chosen_indices = resolve_select_indices(
            bank_questions,
            directive["select"],
            str(directive["_include"]),
            error_cls=QuizMLError,
        )
        return _select_commented_seq(bank_questions, chosen_indices)

    if "count" in directive:
        try:
            count = int(directive["count"])
        except (TypeError, ValueError) as err:
            raise QuizMLError("Include 'count' must be an integer") from err
        if count < 0:
            raise QuizMLError("Include 'count' cannot be negative")
        if count > len(bank_questions):
            raise QuizMLError(
                f"Include 'count' ({count}) exceeds available questions "
                f"({len(bank_questions)}) in {directive['_include']!s}"
            )
        seed = directive.get("seed", child_seed)
        if seed is None:
            raise QuizMLError(
                "Sampled includes require a 'seed' or a command-line --seed"
            )
        if count < len(bank_questions):
            return _sample_questions(bank_questions, count, seed)
        return bank_questions

    if "seed" in directive:
        raise QuizMLError("Include 'seed' requires a 'count'")

    return bank_questions


def expand_roundtrip_includes(
    questions: list[Any],
    base_dir: Path,
    *,
    inherited_seed: Any,
    stack: tuple[Path, ...],
    figure_dirs: list[Path],
) -> CommentedSeq:
    """Expand ``_include`` directives (select, count/seed) preserving comments."""
    expanded = CommentedSeq()

    for index, question in enumerate(questions):
        source_comments = getattr(questions, "ca", None)
        question_comments = (
            source_comments.items.get(index) if source_comments is not None else None
        )
        if (
            isinstance(question, dict)
            and "include" in question
            and "type" not in question
        ):
            raise QuizMLError("Unknown directive 'include'. Did you mean '_include'?")
        if not isinstance(question, dict) or "_include" not in question:
            _append_commented_items(expanded, [question], [question_comments])
            continue

        unknown_keys = set(question) - {"_include", "count", "seed", "select"}
        if unknown_keys:
            unknown = ", ".join(sorted(str(k) for k in unknown_keys))
            raise QuizMLError(f"Unknown key(s) on '_include' item: {unknown}")
        if "select" in question and ("count" in question or "seed" in question):
            raise QuizMLError(
                "Cannot combine 'select' with 'count' or 'seed' on '_include' item"
            )

        include_path = (base_dir / str(question["_include"])).expanduser().resolve()
        if include_path in stack:
            chain = " -> ".join(str(path) for path in (*stack, include_path))
            raise QuizMLError(f"Circular include detected: {chain}")
        try:
            _, bank_docs, q_index = read_roundtrip_yaml(include_path)
        except QuizMLError as err:
            raise QuizMLError(f"In include {question['_include']!s}: {err}") from err
        bank_questions = bank_docs[q_index] if q_index is not None else []
        figure_dirs.append(include_path.parent.resolve())
        if q_index == 1:
            figure_dirs.extend(extract_figure_paths(bank_docs[0], include_path.parent))

        # Derive a deterministic per-include seed from the parent seed and item index
        # so sibling includes with the same parent seed sample independently.
        child_seed = f"{inherited_seed}:{index}" if inherited_seed is not None else None
        bank_questions = expand_roundtrip_includes(
            bank_questions,
            include_path.parent,
            inherited_seed=child_seed,
            stack=(*stack, include_path),
            figure_dirs=figure_dirs,
        )
        bank_questions = _apply_roundtrip_filter(bank_questions, question, child_seed)

        comments = [bank_questions.ca.items.get(i) for i in range(len(bank_questions))]
        directive_comments = _comment_tokens(question)
        if comments and directive_comments:
            if comments[0] is None:
                comments[0] = [None, directive_comments, None, None]
            else:
                before = comments[0][1]
                comments[0][1] = (
                    directive_comments
                    if before is None
                    else [*directive_comments, *before]
                )
        if comments and question_comments:
            comments[0] = _merge_comment_slots(
                comments[0], question_comments, as_list=False
            )
        _append_commented_items(expanded, bank_questions, comments)

    if getattr(questions, "ca", None):
        expanded.ca.comment = copy.deepcopy(questions.ca.comment)
        expanded.ca.end = copy.deepcopy(questions.ca.end)
    return expanded
