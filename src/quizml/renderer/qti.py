"""IMS QTI 1.2 package renderer and ZIP packager."""

import base64
import hashlib
import io
import re
import warnings
import zipfile
from pathlib import Path

from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning

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
    qti_opts = (
        dict(header.get("_qti", {})) if isinstance(header.get("_qti"), dict) else {}
    )

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
    if show_correct_answers_at is None and release_solutions in (
        "after_due_date",
        "after_deadline",
    ):
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


def _process_qti_html(html_str: str, media_store: dict) -> tuple[str, list[str]]:
    """Sanitizes HTML for QTI: cleans tables and extracts data URI images into assets.

    LMSs like Blackboard Ultra flatten HTML tables when nested in <div>, using
    <thead>/<tbody>, or when burdened with complex inline CSS styles.
    Similarly, LMS QTI importers fail on base64 data URIs and require external files
    declared in imsmanifest.xml.

    :param html_str: Raw XHTML / HTML string.
    :param media_store: Dict collecting {relative_filename: bytes}.
    :return: (cleaned_xhtml, list_of_referenced_media_files)
    """
    if not html_str:
        return "", []

    warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)
    soup = BeautifulSoup(str(html_str), "html.parser")
    referenced_media = []

    # 1. Clean tables for LMS compatibility
    for div in soup.find_all("div"):
        div.unwrap()

    for table in soup.find_all("table"):
        for container in table.find_all(["thead", "tbody", "tfoot"]):
            container.unwrap()
        table.attrs = {"border": "1", "style": "border-collapse: collapse;"}
        for tr in table.find_all("tr"):
            tr.attrs = {}
        for cell in table.find_all(["th", "td"]):
            cell.attrs = {}

    # 2. Extract embedded images (data URIs) into external media assets
    for img in soup.find_all("img"):
        src = img.get("src", "")
        if not src.startswith("data:image/"):
            continue

        img_bytes = None
        ext = "png"
        if src.startswith("data:image/svg+xml;base64,"):
            b64_str = src.split(",", 1)[1]
            try:
                raw_svg = base64.b64decode(b64_str).decode("utf-8", errors="replace")
                m = re.search(
                    r'<image[^>]*href="data:image/(png|jpeg|jpg);base64,([^"]+)"',
                    raw_svg,
                )
                if m:
                    ext = "jpg" if m.group(1) == "jpeg" else m.group(1)
                    img_bytes = base64.b64decode(m.group(2))
                else:
                    ext = "svg"
                    img_bytes = raw_svg.encode("utf-8")
            except Exception:
                continue
        else:
            m = re.match(r"data:image/([^;]+);base64,(.+)", src)
            if m:
                ext = "jpg" if m.group(1) == "jpeg" else m.group(1)
                try:
                    img_bytes = base64.b64decode(m.group(2))
                except Exception:
                    continue

        if img_bytes:
            img_hash = hashlib.md5(img_bytes).hexdigest()[:10]
            fname = f"images/img_{img_hash}.{ext}"
            media_store[fname] = img_bytes
            referenced_media.append(fname)
            img["src"] = fname

            if img.has_attr("width"):
                try:
                    img["width"] = str(round(float(img["width"])))
                except (ValueError, TypeError):
                    pass
            if img.has_attr("height"):
                try:
                    img["height"] = str(round(float(img["height"])))
                except (ValueError, TypeError):
                    pass

    cleaned_str = str(soup)
    cleaned_str = _ensure_xhtml(cleaned_str)
    return cleaned_str, referenced_media


def _process_questions_for_qti(questions: list, media_store: dict) -> list:
    """Processes question text, choices, and feedback for tables and media extraction."""
    processed = []
    for q in questions:
        item_q = dict(q)
        item_media = []
        for field in ["question", "feedback", "feedback_correct", "feedback_incorrect"]:
            if field in item_q and item_q[field]:
                cleaned, media = _process_qti_html(item_q[field], media_store)
                item_q[field] = cleaned
                item_media.extend(media)

        if "choices" in item_q and isinstance(item_q["choices"], list):
            cleaned_choices = []
            for c in item_q["choices"]:
                if isinstance(c, dict):
                    c_dict = dict(c)
                    raw_text = (
                        c_dict.get("x") or c_dict.get("o") or c_dict.get("text") or ""
                    )
                    cleaned_text, media = _process_qti_html(
                        _clean_choice_text(raw_text), media_store
                    )
                    c_dict["choice_text"] = cleaned_text
                    item_media.extend(media)
                    if "A" in c_dict:
                        cleaned_a, media = _process_qti_html(
                            _ensure_xhtml(c_dict["A"]), media_store
                        )
                        c_dict["A"] = cleaned_a
                        item_media.extend(media)
                    if "B" in c_dict:
                        cleaned_b, media = _process_qti_html(
                            _ensure_xhtml(c_dict["B"]), media_store
                        )
                        c_dict["B"] = cleaned_b
                        item_media.extend(media)
                    cleaned_choices.append(c_dict)
                else:
                    cleaned_c, media = _process_qti_html(
                        _clean_choice_text(c), media_store
                    )
                    cleaned_choices.append(cleaned_c)
                    item_media.extend(media)
            item_q["choices"] = cleaned_choices

        item_q["media_files"] = list(dict.fromkeys(item_media))
        processed.append(item_q)
    return processed


def _render_qti12(qti_ctx: dict, tdir: Path) -> bytes:
    """Renders a QTI 1.2 package directory into an in-memory ZIP archive."""
    media_store: dict[str, bytes] = {}
    render_ctx = dict(qti_ctx)
    render_ctx["questions"] = _process_questions_for_qti(
        qti_ctx.get("questions", []), media_store
    )
    render_ctx["all_media_files"] = list(media_store.keys())

    quiz_xml = render_template(render_ctx, tdir / "quiz.xml.j2")
    manifest_xml = render_template(render_ctx, tdir / "imsmanifest.xml.j2")
    meta_xml = render_template(render_ctx, tdir / "assessment_meta.xml.j2")

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("quiz.xml", quiz_xml.encode("utf-8"))
        zf.writestr("imsmanifest.xml", manifest_xml.encode("utf-8"))
        zf.writestr("assessment_meta.xml", meta_xml.encode("utf-8"))
        for fname, bdata in media_store.items():
            zf.writestr(fname, bdata)

    return buf.getvalue()


def _render_qti21(qti_ctx: dict, tdir: Path) -> bytes:
    """Renders a QTI 2.1 package directory into an in-memory ZIP archive."""
    media_store: dict[str, bytes] = {}
    processed_questions = _process_questions_for_qti(
        qti_ctx.get("questions", []), media_store
    )

    render_ctx = dict(qti_ctx)
    render_ctx["questions"] = processed_questions
    render_ctx["all_media_files"] = list(media_store.keys())

    manifest_xml = render_template(render_ctx, tdir / "imsmanifest.xml.j2")
    assessment_xml = (
        render_template(render_ctx, tdir / "assessment.xml.j2")
        if (tdir / "assessment.xml.j2").exists()
        else None
    )

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("imsmanifest.xml", manifest_xml.encode("utf-8"))
        if assessment_xml:
            zf.writestr("assessment.xml", assessment_xml.encode("utf-8"))

        item_template = tdir / "item.xml.j2"
        for idx, item_q in enumerate(processed_questions, start=1):
            item_ctx = dict(render_ctx)
            item_ctx["q"] = item_q
            item_ctx["item_index"] = idx
            item_xml = render_template(item_ctx, item_template)
            zf.writestr(f"items/item_{idx}.xml", item_xml.encode("utf-8"))

        # Write media assets to both images/ and items/images/ for maximum LMS compatibility
        for fname, bdata in media_store.items():
            zf.writestr(fname, bdata)
            zf.writestr(f"items/{fname}", bdata)

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
