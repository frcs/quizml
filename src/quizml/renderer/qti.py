"""IMS QTI 1.2 package renderer and ZIP packager."""

import hashlib
import io
import re
import zipfile
from pathlib import Path

from quizml.renderer.jinja import render_template


def _slugify(text: str) -> str:
    """Produces a clean alphanumeric identifier for XML IDs."""
    clean = re.sub(r"[^a-zA-Z0-9_]", "_", str(text))
    clean = re.sub(r"_+", "_", clean).strip("_")
    return clean or "quiz"


def _derive_duration_from_examtime(examtime: str) -> int | None:
    """Parses time string like '09:30-11:30' into duration in minutes (e.g. 120)."""
    m = re.match(r"(\d{1,2}):(\d{2})\s*-\s*(\d{1,2}):(\d{2})", str(examtime).strip())
    if m:
        h1, m1, h2, m2 = map(int, m.groups())
        diff = (h2 * 60 + m2) - (h1 * 60 + m1)
        return diff if diff > 0 else None
    return None


def _strip_html(text: str) -> str:
    """Strips HTML tags (e.g. <p>...</p>) to produce clean plain text."""
    clean = re.sub(r"<[^>]+>", "", str(text))
    return " ".join(clean.strip().split())


def prepare_qti_context(context: dict) -> dict:
    """Normalizes document header metadata into structured QTI properties."""
    header = context.get("header", {})
    qti_opts = dict(header.get("_qti", {})) if isinstance(header.get("_qti"), dict) else {}

    title = (
        qti_opts.get("title")
        or header.get("title")
        or header.get("modulename")
        or header.get("inputbasename")
        or "QuizML Assessment"
    )
    title = _strip_html(title)

    raw_ident = header.get("inputbasename") or title
    assessment_hash = hashlib.md5(raw_ident.encode("utf-8")).hexdigest()[:8]
    assessment_ident = f"qti_{_slugify(raw_ident)[:30]}_{assessment_hash}"

    time_limit = qti_opts.get("time_limit")
    if time_limit is None and "examtime" in header:
        time_limit = _derive_duration_from_examtime(header["examtime"])
    if time_limit is not None:
        try:
            time_limit = int(time_limit)
        except (ValueError, TypeError):
            time_limit = None

    due_at = qti_opts.get("due_at")
    release_results = qti_opts.get("release_results", "after_submission")
    release_score = qti_opts.get("release_score", release_results)
    release_solutions = qti_opts.get("release_solutions", release_results)
    release_date = qti_opts.get("release_date")

    # Canvas mapping for result release
    show_correct_answers_at = qti_opts.get("show_correct_answers_at")
    if show_correct_answers_at is None and release_solutions in ("after_due_date", "after_deadline"):
        show_correct_answers_at = due_at
    elif show_correct_answers_at is None and release_solutions == "on_date":
        show_correct_answers_at = release_date

    hide_results = qti_opts.get("hide_results")
    if hide_results is None:
        if release_score in ("manual", "never"):
            hide_results = "always"
        elif release_score in ("after_due_date", "after_deadline"):
            hide_results = "until_after_last_attempt"

    qti_context = dict(context)
    qti_context["qti"] = {
        "title": title,
        "assessment_ident": assessment_ident,
        "description": qti_opts.get("description") or header.get("instructions", ""),
        "quiz_type": qti_opts.get("quiz_type", "assignment"),
        "time_limit": time_limit,
        "due_at": due_at,
        "allowed_attempts": qti_opts.get("allowed_attempts", 1),
        "scoring_policy": qti_opts.get("scoring_policy", "keep_highest"),
        "shuffle_answers": bool(qti_opts.get("shuffle_answers", False)),
        "release_results": release_results,
        "release_score": release_score,
        "release_solutions": release_solutions,
        "release_date": release_date,
        "show_correct_answers_at": show_correct_answers_at,
        "hide_results": hide_results,
        "access_code": qti_opts.get("access_code"),
        "ip_filter": qti_opts.get("ip_filter"),
        "one_question_at_a_time": bool(qti_opts.get("one_question_at_a_time", False)),
        "cant_go_back": bool(qti_opts.get("cant_go_back", False)),
    }
    return qti_context


def _render_qti12(qti_ctx: dict, tdir: Path) -> bytes:
    """Renders a QTI 1.2 package directory into an in-memory ZIP archive."""
    quiz_xml = render_template(qti_ctx, tdir / "quiz.xml.j2")
    manifest_xml = render_template(qti_ctx, tdir / "imsmanifest.xml.j2")
    meta_xml = render_template(qti_ctx, tdir / "assessment_meta.xml.j2")

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("quiz.xml", quiz_xml.encode("utf-8"))
        zf.writestr("imsmanifest.xml", manifest_xml.encode("utf-8"))
        zf.writestr("assessment_meta.xml", meta_xml.encode("utf-8"))

    return buf.getvalue()


def _ensure_xhtml(html_str: str) -> str:
    """Ensures HTML void tags (br, hr, img) are XML self-closing and well-formed."""
    if not html_str:
        return ""
    cleaned = re.sub(r"<br\s*(?<!/)>", "<br/>", str(html_str), flags=re.IGNORECASE)
    cleaned = re.sub(r"<hr\s*(?<!/)>", "<hr/>", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"(<img\b[^>]*?)(?<!/)>", r"\1/>", cleaned, flags=re.IGNORECASE)
    return cleaned


def _clean_choice_text(val) -> str:
    """Strips outer paragraph tag from simple choice text if it's a single paragraph."""
    s = str(val).strip()
    if s.startswith("<p>") and s.endswith("</p>") and s.count("<p>") == 1:
        s = s[3:-4].strip()
    return _ensure_xhtml(s)


def _render_qti21(qti_ctx: dict, tdir: Path) -> bytes:
    """Renders a QTI 2.1 package directory into an in-memory ZIP archive."""
    manifest_xml = render_template(qti_ctx, tdir / "imsmanifest.xml.j2")
    assessment_xml = (
        render_template(qti_ctx, tdir / "assessment.xml.j2")
        if (tdir / "assessment.xml.j2").exists()
        else None
    )

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("imsmanifest.xml", manifest_xml.encode("utf-8"))
        if assessment_xml:
            zf.writestr("assessment.xml", assessment_xml.encode("utf-8"))

        item_template = tdir / "item.xml.j2"
        questions = qti_ctx.get("questions", [])
        for idx, q in enumerate(questions, start=1):
            item_q = dict(q)
            if "question" in item_q:
                item_q["question"] = _ensure_xhtml(item_q["question"])
            if "feedback" in item_q:
                item_q["feedback"] = _ensure_xhtml(item_q["feedback"])
            if "feedback_correct" in item_q:
                item_q["feedback_correct"] = _ensure_xhtml(item_q["feedback_correct"])
            if "feedback_incorrect" in item_q:
                item_q["feedback_incorrect"] = _ensure_xhtml(item_q["feedback_incorrect"])
            if "choices" in item_q and isinstance(item_q["choices"], list):
                cleaned_choices = []
                for c in item_q["choices"]:
                    if isinstance(c, dict):
                        c_dict = dict(c)
                        raw_text = c_dict.get("x") or c_dict.get("o") or c_dict.get("text") or ""
                        c_dict["choice_text"] = _clean_choice_text(raw_text)
                        if "A" in c_dict:
                            c_dict["A"] = _ensure_xhtml(c_dict["A"])
                        if "B" in c_dict:
                            c_dict["B"] = _ensure_xhtml(c_dict["B"])
                        cleaned_choices.append(c_dict)
                    else:
                        cleaned_choices.append(_clean_choice_text(c))
                item_q["choices"] = cleaned_choices

            item_ctx = dict(qti_ctx)
            item_ctx["q"] = item_q
            item_ctx["item_index"] = idx
            item_xml = render_template(item_ctx, item_template)
            zf.writestr(f"items/item_{idx}.xml", item_xml.encode("utf-8"))

    return buf.getvalue()


def render_qti(context: dict, template_dir: Path | str) -> bytes:
    """Renders a multi-file QTI (1.2 or 2.1) package directory into an in-memory ZIP archive (bytes).

    :param context: Render context containing 'header' and 'questions'.
    :param template_dir: Path to directory containing QTI templates.
    :return: Binary zip archive content.
    """
    tdir = Path(template_dir)
    qti_ctx = prepare_qti_context(context)

    if (tdir / "quiz.xml.j2").exists():
        return _render_qti12(qti_ctx, tdir)
    elif (tdir / "item.xml.j2").exists():
        return _render_qti21(qti_ctx, tdir)
    else:
        raise FileNotFoundError(
            f"No recognizable QTI template found in {tdir} (expected quiz.xml.j2 or item.xml.j2)"
        )

