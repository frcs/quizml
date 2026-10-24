"""Unified question-bank _include, select, and deterministic sampling engine."""

import copy
import os
import random
from pathlib import Path

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


def resolve_include_path(filename, base_dir: Path) -> Path:
    found = find_path(filename, [base_dir])
    if found:
        return found[0]
    requested = Path(filename).expanduser()
    if not requested.is_absolute():
        requested = Path(base_dir) / requested
    return Path(os.path.realpath(requested))


def normalize_select_list(select_spec, error_cls=QuizMLYamlSyntaxError) -> list[str]:
    if isinstance(select_spec, list):
        return [str(x).strip() for x in select_spec if str(x).strip()]
    if isinstance(select_spec, (str, int)):
        return [s.strip() for s in str(select_spec).split(",") if s.strip()]
    raise error_cls(
        "Include 'select' must be a list or comma-separated string of question IDs or 1-based indices."
    )


def resolve_select_indices(
    questions: list, select_spec, source_label, error_cls=QuizMLYamlSyntaxError
) -> list[int]:
    """Return 0-based indices of questions matching a 'select' specification (by ID or 1-based index)."""
    selectors = normalize_select_list(select_spec, error_cls=error_cls)
    by_id = {
        str(q["id"]).strip(): idx
        for idx, q in enumerate(questions)
        if isinstance(q, dict) and q.get("id")
    }
    chosen_indices = []
    for sel in selectors:
        if sel in by_id:
            chosen_indices.append(by_id[sel])
        elif sel.isdigit():
            pos = int(sel)
            if 1 <= pos <= len(questions):
                chosen_indices.append(pos - 1)
            else:
                raise error_cls(
                    f"Include 'select' index {pos} is out of range (1..{len(questions)}) in '{source_label}'."
                )
        else:
            raise error_cls(
                f"Include 'select' ID '{sel}' not found in '{source_label}'."
            )
    return chosen_indices


def select_questions(questions: list, select_spec, source_label) -> list:
    indices = resolve_select_indices(
        questions, select_spec, source_label, error_cls=QuizMLYamlSyntaxError
    )
    return [questions[i] for i in indices]


def count_included_questions(
    item: dict, base_dir: Path, visited: set[Path] | None = None
) -> int:
    """Count the questions contributed by an include, recursively."""
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


def _reject_include_sampling(item):
    """Require random sampling directives to be materialized with ``quizml sample``."""
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
    questions_data: list,
    base_dir: Path,
    root_dir: Path,
    visited: set[Path] | None = None,
    accumulated_figure_dirs: list[str] | None = None,
    schema=None,
    source_text="",
    source_path="<string>",
) -> list:
    """Recursively resolve '- _include: filename.yaml' directives for compilation."""
    if visited is None:
        visited = set()
    if accumulated_figure_dirs is None:
        accumulated_figure_dirs = []

    validate_source_questions(
        questions_data, schema, source_text=source_text, source_path=source_path
    )

    resolved = []
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
                    f"Included YAML file not found: '{inc_file}' (resolved to '{inc_path}')"
                )

            if inc_path in visited:
                raise QuizMLYamlSyntaxError(
                    f"Circular include detected: '{inc_path}' is already in the inclusion chain."
                )

            sub_header, sub_questions, inc_text = read_question_file(inc_path)
            validate_header(sub_header, schema, inc_text, str(inc_path))

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


def _select_commented_seq(questions, indices: list[int]) -> CommentedSeq:
    selected = CommentedSeq()
    comment = getattr(questions, "ca", None)
    for source_index in indices:
        selected.append(questions[source_index])
        if comment and source_index in comment.items:
            selected.ca.items[len(selected) - 1] = copy.deepcopy(
                comment.items[source_index]
            )
    return selected


def _sample_questions(questions, count: int, seed) -> CommentedSeq:
    indices = random.Random(str(seed)).sample(range(len(questions)), count)
    return _select_commented_seq(questions, indices)


def _comment_tokens(data):
    ca = getattr(data, "ca", None)
    if ca is None:
        return []
    tokens = []

    def collect(value):
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


def expand_roundtrip_includes(
    questions, base_dir: Path, *, inherited_seed, stack, figure_dirs: list[Path]
):
    """Expand _include directives (including select and count/seed sampling) while preserving ruamel comments."""
    expanded = CommentedSeq()

    def append_items(items, comments=None):
        start = len(expanded)
        expanded.extend(items)
        if comments:
            for offset, comment in enumerate(comments):
                if offset >= len(items) or comment is None:
                    continue
                target_index = start + offset
                existing = expanded.ca.items.get(target_index)
                if existing is None:
                    expanded.ca.items[target_index] = copy.deepcopy(comment)
                else:
                    for slot, value in enumerate(comment):
                        if value is None:
                            continue
                        if existing[slot] is None:
                            existing[slot] = copy.deepcopy(value)
                        elif isinstance(existing[slot], list):
                            values = value if isinstance(value, list) else [value]
                            existing[slot].extend(copy.deepcopy(values))
                        else:
                            existing[slot] = [existing[slot], copy.deepcopy(value)]

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
            append_items([question], [question_comments])
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

        child_seed = f"{inherited_seed}:{index}" if inherited_seed is not None else None
        bank_questions = expand_roundtrip_includes(
            bank_questions,
            include_path.parent,
            inherited_seed=child_seed,
            stack=(*stack, include_path),
            figure_dirs=figure_dirs,
        )

        if "select" in question:
            chosen_indices = resolve_select_indices(
                bank_questions,
                question["select"],
                str(question["_include"]),
                error_cls=QuizMLError,
            )
            bank_questions = _select_commented_seq(bank_questions, chosen_indices)
        elif "count" in question:
            try:
                count = int(question["count"])
            except (TypeError, ValueError) as err:
                raise QuizMLError("Include 'count' must be an integer") from err
            if count < 0:
                raise QuizMLError("Include 'count' cannot be negative")
            if count > len(bank_questions):
                raise QuizMLError(
                    f"Include 'count' ({count}) exceeds available questions ({len(bank_questions)}) in {question['_include']!s}"
                )
            seed = question.get("seed", child_seed)
            if seed is None:
                raise QuizMLError(
                    "Sampled includes require a 'seed' or a command-line --seed"
                )
            if count < len(bank_questions):
                bank_questions = _sample_questions(bank_questions, count, seed)
        elif "seed" in question:
            raise QuizMLError("Include 'seed' requires a 'count'")

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
            if comments[0] is None:
                comments[0] = question_comments
            else:
                for slot, value in enumerate(question_comments):
                    if value is not None:
                        current = comments[0][slot]
                        comments[0][slot] = (
                            copy.deepcopy(value)
                            if current is None
                            else [current, copy.deepcopy(value)]
                        )
        append_items(bank_questions, comments)

    if getattr(questions, "ca", None):
        expanded.ca.comment = copy.deepcopy(questions.ca.comment)
        expanded.ca.end = copy.deepcopy(questions.ca.end)
    return expanded
