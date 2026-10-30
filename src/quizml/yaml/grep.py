"""Question search and grep functionality across QuizML YAML files."""

import io
import logging
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML
from ruamel.yaml.error import StreamMark
from ruamel.yaml.tokens import CommentToken

from quizml.exceptions import QuizMLError
from quizml.yaml.diff import questions_are_similar
from quizml.yaml.format import clean_all_q_comments, wrap_text_fields
from quizml.yaml.parser import parse_roundtrip_yaml_text, read_roundtrip_yaml


@dataclass
class GrepMatch:
    """Represents a single matching question with provenance metadata."""

    file_path: Path
    question_index: int
    question_id: str | None
    question_data: dict[str, Any]
    also_in: list[tuple[Path, int, str | None]] = field(default_factory=list)

    @property
    def question_type(self) -> str:
        return str(self.question_data.get("type", "unknown"))

    @property
    def marks(self) -> Any:
        return self.question_data.get("marks", "")

    @property
    def statement_excerpt(self) -> str:
        q_text = str(self.question_data.get("question", "")).strip()
        first_line = q_text.splitlines()[0] if q_text else ""
        return first_line[:80] + ("..." if len(first_line) > 80 else "")


def extract_strings(data: Any) -> list[str]:
    """Recursively extract string values from question dictionary or choices."""
    results: list[str] = []
    if isinstance(data, str):
        results.append(data)
    elif isinstance(data, dict):
        for k, v in data.items():
            results.append(str(k))
            results.extend(extract_strings(v))
    elif isinstance(data, (list, tuple)):
        for item in data:
            results.extend(extract_strings(item))
    return results


def is_question_match(
    question: dict[str, Any],
    pattern: str = "",
    *,
    regex: re.Pattern | None = None,
    fixed_strings: bool = False,
    ignore_case: bool = False,
    invert_match: bool = False,
    field: str | None = None,
    qtype: str | None = None,
) -> bool:
    """Check if a question mapping matches search criteria."""
    if qtype:
        actual_type = str(question.get("type", "")).strip().lower()
        if actual_type != qtype.strip().lower():
            return False

    if field:
        if field not in question:
            matched = False
        else:
            values = extract_strings(question[field])
            matched = any(
                _match_text(
                    v,
                    pattern,
                    regex=regex,
                    fixed_strings=fixed_strings,
                    ignore_case=ignore_case,
                )
                for v in values
            )
    else:
        values = extract_strings(question)
        matched = any(
            _match_text(
                v,
                pattern,
                regex=regex,
                fixed_strings=fixed_strings,
                ignore_case=ignore_case,
            )
            for v in values
        )

    return not matched if invert_match else matched


def _match_text(
    text: str,
    pattern: str,
    *,
    regex: re.Pattern | None = None,
    fixed_strings: bool = False,
    ignore_case: bool = False,
) -> bool:
    if fixed_strings:
        if pattern == "":
            return True
        if ignore_case:
            return pattern.lower() in text.lower()
        return pattern in text
    if regex is not None:
        return bool(regex.search(text))
    flags = re.IGNORECASE if ignore_case else 0
    effective_pattern = ".*" if pattern in ("", "*") else pattern
    return bool(re.search(effective_pattern, text, flags))


def find_quiz_files_for_grep(
    paths: list[str | Path] | None = None,
    *,
    recursive: bool = True,
) -> list[Path]:
    """Discover quiz YAML files given a list of file or directory paths."""
    if not paths:
        paths = ["."]

    candidates: list[Path] = []
    seen: set[Path] = set()

    for p in paths:
        if str(p) == "-":
            stdin_path = Path("-")
            if stdin_path not in seen:
                candidates.append(stdin_path)
                seen.add(stdin_path)
            continue

        resolved = Path(p).expanduser().resolve()
        if not resolved.exists():
            raise QuizMLError(f"Path does not exist: {p}")

        if resolved.is_file():
            if resolved not in seen:
                candidates.append(resolved)
                seen.add(resolved)
        elif resolved.is_dir():
            pattern = "**/*" if recursive else "*"
            for ext in (".yaml", ".yml"):
                for file_candidate in resolved.glob(f"{pattern}{ext}"):
                    # Skip hidden directories (like .git, .devlog) and hidden files
                    try:
                        rel = file_candidate.relative_to(resolved)
                        if any(part.startswith(".") for part in rel.parts):
                            continue
                    except ValueError:
                        if file_candidate.name.startswith("."):
                            continue
                    if file_candidate.is_file() and file_candidate not in seen:
                        candidates.append(file_candidate)
                        seen.add(file_candidate)

    return sorted(candidates, key=lambda x: str(x))


def grep_questions(
    pattern: str = "",
    paths: list[str | Path] | None = None,
    *,
    ignore_case: bool = False,
    fixed_strings: bool = False,
    invert_match: bool = False,
    field: str | None = None,
    qtype: str | None = None,
    unique: bool = False,
    recursive: bool = True,
    base_dir: Path | None = None,
) -> list[GrepMatch]:
    """Search questions across files matching the pattern."""
    pattern_str = pattern if pattern is not None else ""
    effective_pattern = ".*" if pattern_str in ("", "*") else pattern_str

    compiled_regex: re.Pattern | None = None
    if not fixed_strings:
        flags = re.IGNORECASE if ignore_case else 0
        try:
            compiled_regex = re.compile(effective_pattern, flags)
        except re.error as err:
            raise QuizMLError(f"Invalid regular expression '{pattern}': {err}") from err

    file_paths = find_quiz_files_for_grep(paths, recursive=recursive)
    explicit_files: set[Path] = set()
    if paths:
        for p in paths:
            if str(p) != "-":
                resolved_p = Path(p).expanduser().resolve()
                if resolved_p.is_file():
                    explicit_files.add(resolved_p)
    matches: list[GrepMatch] = []

    for file_path in file_paths:
        if str(file_path) == "-":
            raw_text = sys.stdin.read()
            _yaml_obj, docs, q_index = parse_roundtrip_yaml_text(raw_text, "<stdin>")
            display_path = Path("<stdin>")
        else:
            try:
                _yaml_obj, docs, q_index = read_roundtrip_yaml(file_path)
            except QuizMLError as err:
                if file_path in explicit_files:
                    raise
                logging.debug(f"Skipping unparseable YAML file {file_path}: {err}")
                continue
            display_path = (
                file_path.relative_to(base_dir)
                if base_dir and file_path.is_relative_to(base_dir)
                else file_path
            )

        if q_index is None:
            continue

        questions = docs[q_index]
        if not isinstance(questions, list):
            continue

        for idx, q in enumerate(questions, start=1):
            if not isinstance(q, dict):
                continue
            if is_question_match(
                q,
                pattern,
                regex=compiled_regex,
                fixed_strings=fixed_strings,
                ignore_case=ignore_case,
                invert_match=invert_match,
                field=field,
                qtype=qtype,
            ):
                q_id = str(q.get("id")).strip() if q.get("id") else None

                if unique:
                    # Check if similar to an existing match
                    collapsed = False
                    for existing in matches:
                        if questions_are_similar(existing.question_data, q):
                            existing.also_in.append((display_path, idx, q_id))
                            collapsed = True
                            break
                    if collapsed:
                        continue

                matches.append(
                    GrepMatch(
                        file_path=display_path,
                        question_index=idx,
                        question_id=q_id,
                        question_data=q,
                    )
                )

    return matches


def format_matching_questions(
    matches: list[GrepMatch],
    *,
    wrap_width: int | None = None,
    show_provenance: bool = True,
) -> str:
    """Format matching questions into standard QuizML YAML with provenance comments."""
    if not matches:
        return ""

    yaml = YAML()
    yaml.indent(mapping=2, sequence=2, offset=0)
    yaml.preserve_quotes = True

    dummy = StreamMark(None, 0, 0, 0)
    seq = yaml.load("[]")

    for i, match in enumerate(matches):
        q_copy = match.question_data.copy()
        clean_all_q_comments(q_copy)
        if hasattr(q_copy, "ca"):
            q_copy.ca.comment = None
            q_copy.ca.items.clear()
            q_copy.ca.end = None

        seq.append(q_copy)

        if show_provenance:
            id_info = f" (id: {match.question_id})" if match.question_id else ""
            prov_lines = [f"# {match.file_path}: <Q{match.question_index}>{id_info}\n"]
            if match.also_in:
                other_refs = ", ".join(f"{f}: <Q{idx}>" for f, idx, _ in match.also_in)
                prov_lines.append(f"# also in: {other_refs}\n")
            prefix = "\n" if i > 0 else ""
            full_comment = prefix + "".join(prov_lines)
            seq.ca.items[i] = [
                None,
                [CommentToken(full_comment, dummy, None, 0)],
                None,
                None,
            ]
        elif i > 0:
            seq.ca.items[i] = [
                None,
                [CommentToken("\n", dummy, None, 0)],
                None,
                None,
            ]

    wrap_text_fields(seq, wrap_width=wrap_width)
    buf = io.StringIO()
    yaml.dump(seq, buf)
    return buf.getvalue().rstrip() + "\n"
