"""Word (.docx) template rendering using docxtpl."""

import io
import logging
import os
import re
from pathlib import Path

from markupsafe import Markup

from quizml.exceptions import QuizMLError


def _xml_escape(text: str) -> str:
    """Escapes XML special characters: &, <, >."""
    if not text:
        return ""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _ensure_run_xml(val, part=None) -> Markup:
    """Ensures value is an OpenXML <w:r> run or <m:oMath> element."""
    if val is None:
        return Markup("")
    s = _clean_docx_str(str(val), part=part)
    if "<w:p" in s:
        # Strip outer paragraph tags
        s = re.sub(r"^<w:p[^>]*>(?:<w:pPr>.*?</w:pPr>)?", "", s, flags=re.DOTALL)
        s = re.sub(r"</w:p>$", "", s, flags=re.DOTALL)
        # Convert internal paragraph breaks into run breaks
        s = re.sub(
            r"</w:p>\s*<w:p[^>]*>(?:<w:pPr>.*?</w:pPr>)?",
            '<w:r><w:br/></w:r>',
            s,
            flags=re.DOTALL,
        )
    elif not (s.startswith("<w:r") or s.startswith("<m:oMath")):
        escaped = _xml_escape(s)
        s = f'<w:r><w:t xml:space="preserve">{escaped}</w:t></w:r>'
    return Markup(s)


def _ensure_block_xml(val, part=None) -> Markup:
    """Ensures value is wrapped in OpenXML block tags (<w:p> or <w:tbl>)."""
    if val is None:
        return Markup("")
    s = _clean_docx_str(str(val), part=part)
    if not (s.startswith("<w:p") or s.startswith("<w:tbl")):
        escaped = _xml_escape(s)
        s = (
            '<w:p><w:pPr><w:spacing w:line="360" w:lineRule="auto"/>'
            '<w:rPr><w:rFonts w:ascii="Calibri" w:hAnsi="Calibri"/><w:sz w:val="24"/></w:rPr></w:pPr>'
            f'<w:r><w:t xml:space="preserve">{escaped}</w:t></w:r></w:p>'
        )
    return Markup(s)


def _xml_to_plain_text(val: str, sep: str = "\n") -> str:
    """Strips all OpenXML tags and returns plain text, preserving line breaks."""
    if not isinstance(val, str):
        return str(val) if val is not None else ""
    if "<w:p" in val or "<w:t" in val:
        import xml.etree.ElementTree as ET

        try:
            root = ET.fromstring(
                f'<root xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">{val}</root>'
            )
            p_list = [el for el in root.iter() if el.tag.endswith("}p") or el.tag == "p"]
            if p_list:
                p_texts = []
                for p in p_list:
                    runs = []
                    for child in p.iter():
                        if (child.tag.endswith("}t") or child.tag == "t") and child.text:
                            runs.append(child.text)
                        elif child.tag.endswith("}br") or child.tag == "br":
                            runs.append("\n")
                    if runs:
                        p_texts.append("".join(runs).strip())
                return sep.join(p_texts).strip()

            t_list = [
                el.text
                for el in root.iter()
                if (el.tag.endswith("}t") or el.tag == "t") and el.text
            ]
            if t_list:
                return "".join(t_list).strip()
        except Exception:
            pass
    clean = re.sub(r"</w:p>", "\n", val)
    clean = re.sub(r"<[^>]+>", "", clean)
    return clean.strip()


def _format_instructions_xml(val: str, part=None) -> Markup:
    """Formats instructions into one or more bold Calibri 12pt <w:p> paragraphs."""
    text = val if isinstance(val, str) else ""
    if not text.strip():
        text = "Please answer all questions."

    paras = []
    if "<w:p" in text:
        import xml.etree.ElementTree as ET

        try:
            root = ET.fromstring(
                f'<root xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">{text}</root>'
            )
            p_list = [el for el in root.iter() if el.tag.endswith("}p") or el.tag == "p"]
            for p in p_list:
                runs = []
                for child in p.iter():
                    if (child.tag.endswith("}t") or child.tag == "t") and child.text:
                        runs.append(child.text)
                    elif child.tag.endswith("}br") or child.tag == "br":
                        runs.append(" ")
                if runs:
                    paras.append("".join(runs).strip())
        except Exception:
            pass

    if not paras:
        clean = re.sub(r"</w:p>", "\n\n", text)
        clean = re.sub(r"<[^>]+>", "", clean)
        paras = [p.strip() for p in clean.split("\n\n") if p.strip()]

    if not paras:
        paras = ["Please answer all questions."]

    p_xmls = []
    for b in paras:
        escaped = _xml_escape(b)
        p_xmls.append(
            '<w:p><w:pPr><w:spacing w:line="360" w:lineRule="auto"/>'
            '<w:rPr><w:rFonts w:ascii="Calibri" w:hAnsi="Calibri"/><w:b/><w:sz w:val="24"/></w:rPr></w:pPr>'
            f'<w:r><w:rPr><w:rFonts w:ascii="Calibri" w:hAnsi="Calibri"/><w:b/><w:sz w:val="24"/></w:rPr>'
            f'<w:t xml:space="preserve">{escaped}</w:t></w:r></w:p>'
        )
    return Markup("".join(p_xmls))


def _clean_docx_str(s: str, part=None) -> str:
    if not isinstance(s, str) or not s:
        return s

    # Resolve any image markers into OpenXML drawing elements
    def _replace_img(m):
        img_path = m.group(1)
        width_val = float(m.group(2))
        if part and os.path.exists(img_path):
            from docx.shared import Inches

            try:
                pic = part.new_pic_inline(img_path, width=Inches(width_val))
                return f'<w:r><w:drawing>{pic.xml}</w:drawing></w:r>'
            except Exception as err:
                logging.warning(f"Failed to embed image {img_path} in docx: {err}")
        return ""

    s = re.sub(r"<!--QUIZML_IMG:([^:]+):([^>]+)-->", _replace_img, s)

    # Strip <style> blocks
    s = re.sub(r"<style[^>]*>.*?</style>", "", s, flags=re.DOTALL)
    # Strip or unwrap div and span tags
    s = re.sub(r"</?(?:div|span)[^>]*>", "", s)
    return s


def _prepare_context_for_docx(context: dict, part=None) -> dict:
    """Prepares template context, ensuring questions and choices have valid OpenXML structures."""
    new_ctx = dict(context)

    # Sanitize header fields: instructions as block XML, others as clean plain text
    if "header" in new_ctx and isinstance(new_ctx["header"], dict):
        new_header = dict(new_ctx["header"])
        for k, v in new_header.items():
            if k == "instructions":
                new_header[k] = _format_instructions_xml(v, part=part)
            elif isinstance(v, str):
                new_header[k] = _xml_to_plain_text(v)
        if "instructions" not in new_header or not new_header["instructions"]:
            new_header["instructions"] = _format_instructions_xml("", part=part)
        new_ctx["header"] = new_header

    questions = new_ctx.get("questions", [])
    prepared_questions = []

    for q in questions:
        q_copy = dict(q)
        if "question" in q_copy:
            q_copy["question"] = _ensure_block_xml(q_copy["question"], part=part)
        if q_copy.get("type") == "essay" and "answer" in q_copy and isinstance(q_copy["answer"], (str, Markup)):
            # Essay or model answers as blocks
            q_copy["answer"] = _ensure_block_xml(q_copy["answer"], part=part)

        if "choices" in q_copy and isinstance(q_copy["choices"], list):
            prepared_choices = []
            for c in q_copy["choices"]:
                if isinstance(c, dict):
                    c_copy = {}
                    for k, v in c.items():
                        c_copy[k] = _ensure_run_xml(v, part=part)
                    prepared_choices.append(c_copy)
                else:
                    prepared_choices.append(_ensure_run_xml(c, part=part))
            q_copy["choices"] = prepared_choices

        prepared_questions.append(q_copy)

    new_ctx["questions"] = prepared_questions

    # Candidate identification box
    hdr = new_ctx.get("header", {})
    raw_midterm = hdr.get("midterm") or hdr.get("infomidterm")
    is_midterm = bool(
        raw_midterm
        and (
            raw_midterm is True
            or str(raw_midterm).strip().lower() in ("true", "1", "yes")
        )
    )
    digit_line = "⓪ ① ② ③ ④ ⑤ ⑥ ⑦ ⑧ ⑨"
    new_ctx["candidate_info"] = {
        "is_midterm": is_midterm,
        "line1_label": "Student Name" if is_midterm else "Exam Number",
        "line2_label": "Student Number" if is_midterm else "Seat Number ",
        "mark_instruction": (
            "Mark your student number below"
            if is_midterm
            else "Mark your exam number below"
        ),
        "digit_rows": (
            "\n".join([digit_line] * 8)
            if is_midterm
            else "\n".join([digit_line] * 5)
        ),
    }

    # Generate answer sheet rows for multi-column grid
    is_sol = bool(new_ctx.get("solutions"))
    open_letters = [chr(0x24B6 + i) for i in range(26)]  # Ⓐ, Ⓑ, Ⓒ, ...
    filled_letters = [chr(0x1F150 + i) for i in range(26)]  # 🅐, 🅑, 🅒, ...

    items = []
    for q_idx, q in enumerate(questions, start=1):
        q_type = q.get("type")
        if q_type in ("mc", "ma"):
            choices = q.get("choices", [])
            bubbles = []
            for c_idx, c in enumerate(choices):
                open_char = (
                    open_letters[c_idx]
                    if c_idx < len(open_letters)
                    else f"({chr(ord('A') + c_idx)})"
                )
                filled_char = (
                    filled_letters[c_idx]
                    if c_idx < len(filled_letters)
                    else f"[{chr(ord('A') + c_idx)}]"
                )
                if is_sol:
                    is_correct = isinstance(c, dict) and "x" in c
                    bubbles.append(filled_char if is_correct else open_char)
                else:
                    bubbles.append(open_char)
            bubble_str = " ".join(bubbles)
        elif q_type == "tf":
            ans = str(q.get("answer", "")).strip().lower()
            if is_sol:
                bubble_str = "🅣 Ⓕ" if ans == "true" else "Ⓣ 🅕"
            else:
                bubble_str = "Ⓣ Ⓕ"
        elif q_type == "essay":
            bubble_str = "essay question"
        elif q_type in ("fill", "mfill"):
            bubble_str = "fill-in"
        elif q_type == "num":
            bubble_str = "numeric"
        else:
            bubble_str = str(q_type or "question")

        items.append({
            "num": f"Q.{q_idx}",
            "sep": "\t",
            "bubbles": bubble_str,
        })

    num_items = len(items)
    if num_items > 0:
      col1_len = (num_items + 2) // 3
      col2_len = (num_items + 1) // 3
      col3_len = num_items // 3
      num_rows = col1_len

      col1 = items[0:col1_len]
      col2 = items[col1_len : col1_len + col2_len]
      col3 = items[col1_len + col2_len : num_items]

      empty_cell = {"num": "", "sep": "", "bubbles": ""}
      sheet_rows = []
      for r in range(num_rows):
        sheet_rows.append({
            "c1": col1[r] if r < len(col1) else empty_cell,
            "c2": col2[r] if r < len(col2) else empty_cell,
            "c3": col3[r] if r < len(col3) else empty_cell,
        })
      new_ctx["answer_sheet_rows"] = sheet_rows
    else:
      new_ctx["answer_sheet_rows"] = []

    return new_ctx


def _ensure_editable_bytes(docx_bytes: bytes) -> bytes:
    """Ensures DocSecurity is set to 0 and removes SharePoint server document metadata."""
    import zipfile

    in_buf = io.BytesIO(docx_bytes)
    out_buf = io.BytesIO()
    with zipfile.ZipFile(in_buf, "r") as zin, zipfile.ZipFile(
        out_buf, "w", compression=zipfile.ZIP_DEFLATED
    ) as zout:
        for item in zin.infolist():
            name = item.filename
            # Strip all customXml (SharePoint forms, schemas, documentManagement)
            if name.startswith("customXml/"):
                continue

            # Strip docProps/custom.xml (ContentTypeId linking to SharePoint document library)
            if name == "docProps/custom.xml":
                continue

            content = zin.read(name)

            if name == "_rels/.rels":
                text = content.decode("utf-8")
                text = re.sub(
                    r"<Relationship[^>]*Target=[\"\x27]docProps/custom\.xml[\"\x27][^>]*/>",
                    "",
                    text,
                )
                content = text.encode("utf-8")

            elif name == "word/_rels/document.xml.rels":
                text = content.decode("utf-8")
                text = re.sub(
                    r"<Relationship[^>]*Target=[\"\x27]\.\./customXml/[^\"\x27]+[\"\x27][^>]*/>",
                    "",
                    text,
                )
                content = text.encode("utf-8")

            elif name == "[Content_Types].xml":
                text = content.decode("utf-8")
                text = re.sub(
                    r"<Override[^>]*PartName=[\"\x27]/docProps/custom\.xml[\"\x27][^>]*/>",
                    "",
                    text,
                )
                text = re.sub(
                    r"<Override[^>]*PartName=[\"\x27]/customXml/[^\"\x27]+[\"\x27][^>]*/>",
                    "",
                    text,
                )
                content = text.encode("utf-8")

            elif name == "docProps/app.xml":
                text = content.decode("utf-8")
                text = re.sub(
                    r"<DocSecurity>\d+</DocSecurity>",
                    "<DocSecurity>0</DocSecurity>",
                    text,
                )
                content = text.encode("utf-8")

            zout.writestr(item, content)

    out_buf.seek(0)
    return out_buf.read()


def render_docx(context: dict, template_filename: str | Path) -> bytes:
    """Renders a Word .docx template using docxtpl.

    Returns the bytes of the rendered document.
    """
    try:
        from docxtpl import DocxTemplate
    except ImportError as err:
        raise QuizMLError(
            "The 'docxtpl' package is required for rendering .docx templates. "
            "Please install it with: pip install docxtpl"
        ) from err

    doc = DocxTemplate(str(template_filename))
    doc.init_docx()

    part = doc.docx.part if hasattr(doc, "docx") and doc.docx else None
    prepared_context = _prepare_context_for_docx(context, part=part)

    doc.render(prepared_context, autoescape=True)

    file_stream = io.BytesIO()
    doc.save(file_stream)
    file_stream.seek(0)
    return _ensure_editable_bytes(file_stream.read())

