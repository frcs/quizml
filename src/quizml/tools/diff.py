"""Question similarity comparison and duplicate detection companion tool."""

import difflib
from pathlib import Path

from quizml.quizmlyaml import load


def normalize_text(text) -> str:
    """Normalize whitespace and case."""
    if not isinstance(text, str):
        return str(text)
    return " ".join(text.strip().lower().split())


def get_choices_content(q: dict) -> list[str]:
    """Extracts choices content as a sorted list of strings."""
    choices = q.get("choices", [])
    content = []
    if isinstance(choices, list):
        for c in choices:
            if isinstance(c, dict):
                for v in c.values():
                    content.append(normalize_text(v))
            else:
                content.append(normalize_text(str(c)))
    return sorted(content)


def questions_are_similar(q1: dict, q2: dict, threshold: float = 0.9) -> bool:
    """Checks whether two questions are structurally and textually similar."""
    if q1.get("type") != q2.get("type"):
        return False

    t1 = normalize_text(q1.get("question", ""))
    t2 = normalize_text(q2.get("question", ""))

    matcher = difflib.SequenceMatcher(None, t1, t2)
    if matcher.ratio() < threshold:
        return False

    c1 = get_choices_content(q1)
    c2 = get_choices_content(q2)
    if c1 != c2:
        return False

    f1 = normalize_text(q1.get("figure", ""))
    f2 = normalize_text(q2.get("figure", ""))
    if f1 != f2:
        return False

    return True


def compare_quiz_files(
    ref_file: str | Path, other_files: list[str | Path]
) -> list[dict]:
    """Compares questions from ref_file against questions from other_files.

    Returns a list of dicts for each question in ref_file:
    {
        'index': i + 1,
        'type': q['type'],
        'question': q.get('question', ''),
        'excerpt': excerpt_str,
        'dups': [list of filenames that contain similar questions]
    }
    """
    ref_doc, _ = load(str(ref_file), validate=False)
    ref_questions = ref_doc.get("questions", [])

    other_data = {}
    for f in other_files:
        doc, _ = load(str(f), validate=False)
        other_data[str(f)] = doc.get("questions", [])

    results = []
    for i, qr in enumerate(ref_questions):
        lines = str(qr.get("question", "")).splitlines()
        long_excerpt = (lines[0] if lines else "") + (" […]" if len(lines) > 1 else "")

        if "choices" in qr and isinstance(qr["choices"], list):
            for ans in qr["choices"]:
                if isinstance(ans, dict):
                    val_str = " ".join([str(v) for v in ans.values()])
                else:
                    val_str = str(ans)

                c_lines = val_str.splitlines()
                if c_lines:
                    long_excerpt += f"\n  * {c_lines[0]}" + (
                        " […]" if len(c_lines) > 1 else ""
                    )

        entry = {
            "index": i + 1,
            "type": qr.get("type", "unknown"),
            "excerpt": long_excerpt,
            "dups": [],
        }

        for f_name, dst_questions in other_data.items():
            for qd in dst_questions:
                if questions_are_similar(qr, qd):
                    entry["dups"].append(f_name)
                    break

        results.append(entry)

    return results
