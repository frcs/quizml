"""Question similarity and cross-file comparison logic for QuizML YAML files."""

import difflib
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from quizml.exceptions import QuizMLConfigError


def normalize_text(text: Any) -> str:
    """Normalize whitespace and case for fuzzy text comparison."""
    if not isinstance(text, str):
        return str(text)
    return " ".join(text.strip().lower().split())


def get_choices_content(q: dict[str, Any]) -> list[str]:
    """Extract normalized choice strings from a question mapping as a sorted list."""
    choices = q.get("choices", [])
    content: list[str] = []
    if isinstance(choices, list):
        for c in choices:
            if isinstance(c, dict):
                for v in c.values():
                    content.append(normalize_text(v))
            else:
                content.append(normalize_text(str(c)))
    return sorted(content)


def questions_are_similar(q1: dict[str, Any], q2: dict[str, Any]) -> bool:
    """Determine whether two question mappings represent the same question.

    Similarity heuristics:
    1. If both questions define non-empty ``id`` fields and they match, return True.
    2. Question ``type`` must match.
    3. Normalized question stems must have a ``SequenceMatcher`` ratio >= 0.90.
    4. If choices exist, at least half of the choices must overlap or have a
       combined ``SequenceMatcher`` ratio >= 0.65.
    5. Normalized ``figure`` fields must match.
    """
    id1 = str(q1.get("id") or "").strip()
    id2 = str(q2.get("id") or "").strip()
    if id1 and id2 and id1 == id2:
        return True

    if q1.get("type") != q2.get("type"):
        return False

    t1 = normalize_text(q1.get("question", ""))
    t2 = normalize_text(q2.get("question", ""))

    matcher = difflib.SequenceMatcher(None, t1, t2)
    if matcher.ratio() < 0.9:
        return False

    c1 = get_choices_content(q1)
    c2 = get_choices_content(q2)

    if c1 or c2:
        if not c1 or not c2:
            return False
        overlap = len(set(c1) & set(c2))
        min_needed = max(1, min(len(c1), len(c2)) // 2)
        choice_ratio = difflib.SequenceMatcher(
            None, "\n".join(c1), "\n".join(c2)
        ).ratio()
        if overlap < min_needed and choice_ratio < 0.65:
            return False

    f1 = normalize_text(q1.get("figure", ""))
    f2 = normalize_text(q2.get("figure", ""))

    return f1 == f2


def _format_question_excerpt(qr: dict[str, Any]) -> str:
    """Format a compact multi-line excerpt of a question stem and its choices."""
    lines = str(qr.get("question", "")).splitlines()
    excerpt = (lines[0] if lines else "") + (" […]" if len(lines) > 1 else "")

    choices = qr.get("choices")
    if isinstance(choices, list):
        for ans in choices:
            if isinstance(ans, dict):
                val_str = " ".join(str(v) for v in ans.values())
            else:
                val_str = str(ans)

            choice_lines = val_str.splitlines()
            if choice_lines:
                suffix = " […]" if len(choice_lines) > 1 else ""
                excerpt += f"\n  * {choice_lines[0]}{suffix}"

    return excerpt


def compare_quiz_files(
    files: Sequence[str | Path],
) -> list[dict[str, Any]]:
    """Compare questions in the first file against subsequent files."""
    from quizml.yaml import load

    unique_files = list(dict.fromkeys(files))
    filedata: dict[str | Path, Any] = {}
    for f in unique_files:
        if not Path(f).exists():
            raise QuizMLConfigError(f"File {f} not found")
        filedata[f] = load(f, validate=False)

    ref_yaml = filedata[unique_files[0]]
    ref_questions = ref_yaml["questions"]
    other_files = unique_files[1:]

    qstats: list[dict[str, Any]] = []
    for i, qr in enumerate(ref_questions):
        qstats.append(
            {
                "type": qr.get("type") or "unknown",
                "excerpt": _format_question_excerpt(qr),
            }
        )

        for f in other_files:
            dst_questions = filedata[f]["questions"]
            for qd in dst_questions:
                if questions_are_similar(qr, qd):
                    qstats[i].setdefault("dups", []).append(f)

    return qstats
