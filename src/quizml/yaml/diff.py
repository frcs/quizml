"""Question similarity and cross-file comparison logic for QuizML YAML files."""

import difflib
import os

from quizml.exceptions import QuizMLConfigError


def normalize_text(text):
    """Normalize whitespace and case."""
    if not isinstance(text, str):
        return str(text)
    return " ".join(text.strip().lower().split())


def get_choices_content(q):
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


def questions_are_similar(q1, q2):
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

    if f1 != f2:
        return False

    return True


def compare_quiz_files(files):
    """Compare questions in the first file against subsequent files and return question stats."""
    from quizml.yaml import load

    unique_files = list(dict.fromkeys(files))
    filedata = {}
    for f in unique_files:
        if not os.path.exists(f):
            raise QuizMLConfigError(f"File {f} not found")
        filedata[f] = load(f, validate=False)

    ref_yaml = filedata[unique_files[0]]
    ref_questions = ref_yaml["questions"]
    other_files = unique_files[1:]

    qstats = []
    for i, qr in enumerate(ref_questions):
        lines = str(qr.get("question", "")).splitlines()
        long_excerpt = (lines[0] if lines else "") + (" […]" if len(lines) > 1 else "")

        if "choices" in qr and isinstance(qr["choices"], list):
            for ans in qr["choices"]:
                if isinstance(ans, dict):
                    val_str = " ".join(str(v) for v in ans.values())
                else:
                    val_str = str(ans)

                lines = val_str.splitlines()
                if lines:
                    long_excerpt += f"\n  * {lines[0]}" + (
                        " […]" if len(lines) > 1 else ""
                    )

        qstats.append(
            {"type": qr.get("type") or "unknown", "excerpt": long_excerpt}
        )

        for f in other_files:
            dst_questions = filedata[f]["questions"]
            for qd in dst_questions:
                if questions_are_similar(qr, qd):
                    qstats[i].setdefault("dups", []).append(f)

    return qstats
