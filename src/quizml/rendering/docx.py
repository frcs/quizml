"""Word (.docx) template renderer using docxtpl."""

import io
import logging
import math
import os
import re

import jinja2
from jinja2 import TemplateError
from markupsafe import Markup

from quizml.exceptions import QuizMLConfigError, TemplateRenderError
from quizml.rendering.jinja import _load_filter_callable


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
        s = re.sub(r"^<w:p[^>]*>(?:<w:pPr>.*?</w:pPr>)?", "", s, flags=re.DOTALL)
        s = re.sub(r"</w:p>$", "", s, flags=re.DOTALL)
        s = re.sub(
            r"</w:p>\s*<w:p[^>]*>(?:<w:pPr>.*?</w:pPr>)?",
            "<w:r><w:br/></w:r>",
            s,
            flags=re.DOTALL,
        )
    elif not (s.startswith(("<w:r", "<m:oMath"))):
        escaped = _xml_escape(s)
        s = f'<w:r><w:t xml:space="preserve">{escaped}</w:t></w:r>'
    return Markup(s)


class _DocxHeaderStr(str):
    """Plain-text header string for inline tags that retains OpenXML for block filters."""

    xml: str

    def __new__(cls, plain: str, xml: str = ""):
        obj = super().__new__(cls, plain)
        obj.xml = xml or plain
        return obj


def _ensure_block_xml(val, part=None) -> Markup:
    """Ensures value is wrapped in OpenXML block tags (<w:p> or <w:tbl>)."""
    if val is None or isinstance(val, jinja2.Undefined):
        return Markup("")
    raw = val.xml if isinstance(val, _DocxHeaderStr) else str(val)
    s = _clean_docx_str(str(raw), part=part)
    if not s.strip():
        return Markup("")
    if not (s.startswith(("<w:p", "<w:tbl"))):
        paras = [p.strip() for p in s.split("\n\n") if p.strip()] or [s.strip()]
        p_xmls = []
        for b in paras:
            escaped = _xml_escape(b)
            p_xmls.append(
                '<w:p><w:pPr><w:spacing w:line="360" w:lineRule="auto"/>'
                '<w:rPr><w:rFonts w:ascii="Calibri" w:hAnsi="Calibri"/><w:sz w:val="24"/></w:rPr></w:pPr>'
                f'<w:r><w:t xml:space="preserve">{escaped}</w:t></w:r></w:p>'
            )
        s = "".join(p_xmls)
    return Markup(s)


def _xml_to_plain_text(val: str, sep: str = "\n") -> str:
    """Strips all OpenXML tags and returns plain text, preserving line breaks."""
    if val is None or isinstance(val, jinja2.Undefined):
        return ""
    if not isinstance(val, str):
        return str(val)
    if "<w:p" in val or "<w:t" in val:
        import xml.etree.ElementTree as ET

        try:
            root = ET.fromstring(
                f'<root xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">{val}</root>'
            )
            p_list = [
                el for el in root.iter() if el.tag.endswith("}p") or el.tag == "p"
            ]
            if p_list:
                p_texts = []
                for p in p_list:
                    runs = []
                    for child in p.iter():
                        if (
                            child.tag.endswith("}t") or child.tag == "t"
                        ) and child.text:
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


def _docx_bold_xml(val, part=None) -> Markup:
    """Formats text or OpenXML paragraphs into bold Calibri 12pt <w:p> paragraphs."""
    if val is None or isinstance(val, jinja2.Undefined):
        return Markup("")
    raw = val.xml if isinstance(val, _DocxHeaderStr) else str(val)
    text = str(raw) if raw is not None else ""
    if not text.strip():
        return Markup("")

    paras = []
    if "<w:p" in text:
        import xml.etree.ElementTree as ET

        try:
            root = ET.fromstring(
                f'<root xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">{text}</root>'
            )
            p_list = [
                el for el in root.iter() if el.tag.endswith("}p") or el.tag == "p"
            ]
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

    def _replace_img(m):
        img_path = m.group(1)
        width_val = float(m.group(2))
        if part and os.path.exists(img_path):
            from docx.shared import Inches

            try:
                pic = part.new_pic_inline(img_path, width=Inches(width_val))
                return f"<w:r><w:drawing>{pic.xml}</w:drawing></w:r>"
            except Exception as err:
                logging.warning(f"Failed to embed image {img_path} in docx: {err}")
        return ""

    s = re.sub(r"<!--QUIZML_IMG:([^:]+):([^>]+)-->", _replace_img, s)
    s = re.sub(r"<style[^>]*>.*?</style>", "", s, flags=re.DOTALL)
    s = re.sub(r"</?(?:div|span)[^>]*>", "", s)
    return s


def _prepare_context_for_docx(context: dict, part=None) -> dict:
    """Prepares template context, ensuring questions and choices have valid OpenXML structures."""
    new_ctx = dict(context)

    if "header" in new_ctx and isinstance(new_ctx["header"], dict):
        new_header = {}
        for k, v in new_ctx["header"].items():
            if isinstance(v, str):
                plain = _xml_to_plain_text(v, sep="\n\n")
                new_header[k] = _DocxHeaderStr(plain, xml=str(v))
            else:
                new_header[k] = v
        new_ctx["header"] = new_header

    questions = new_ctx.get("questions", [])
    prepared_questions = []

    for q in questions:
        q_copy = dict(q)
        if "question" in q_copy:
            q_copy["question"] = _ensure_block_xml(q_copy["question"], part=part)
        if q_copy.get("figure"):
            q_copy["figure"] = _ensure_block_xml(q_copy["figure"], part=part)
        if (
            q_copy.get("type") == "essay"
            and "answer" in q_copy
            and isinstance(q_copy["answer"], (str, Markup))
        ):
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
    return new_ctx


def _ensure_editable_bytes(docx_bytes: bytes) -> bytes:
    """Ensures DocSecurity is set to 0 and removes SharePoint server document metadata."""
    import zipfile

    in_buf = io.BytesIO(docx_bytes)
    if not zipfile.is_zipfile(in_buf):
        return docx_bytes
    out_buf = io.BytesIO()
    with (
        zipfile.ZipFile(in_buf, "r") as zin,
        zipfile.ZipFile(out_buf, "w", compression=zipfile.ZIP_DEFLATED) as zout,
    ):
        for item in zin.infolist():
            name = item.filename
            if name.startswith("customXml/"):
                continue
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


def render(context, template_filename, jinja_filters=None):
    """Renders a docx template using docxtpl and returns bytes."""
    try:
        from docxtpl import DocxTemplate
    except ImportError as err:
        raise QuizMLConfigError(
            "The 'docxtpl' package is required for DOCX templates."
        ) from err

    try:
        doc = DocxTemplate(str(template_filename))
        if hasattr(doc, "init_docx"):
            doc.init_docx()

        jinja_env = jinja2.Environment(
            extensions=["jinja2.ext.do"],
            autoescape=True,
        )
        jinja_env.globals["math"] = math
        part = doc.docx.part if hasattr(doc, "docx") and doc.docx else None
        jinja_env.filters["docx_block"] = lambda val: _ensure_block_xml(val, part=part)
        jinja_env.filters["docx_run"] = lambda val: _ensure_run_xml(val, part=part)
        jinja_env.filters["docx_bold"] = lambda val: _docx_bold_xml(val, part=part)
        jinja_env.filters["docx_plain"] = _xml_to_plain_text
        if jinja_filters:
            if not isinstance(jinja_filters, dict):
                raise QuizMLConfigError(
                    "The 'jinja_filters' setting must be a mapping."
                )
            for name, spec in jinja_filters.items():
                jinja_env.filters[name] = _load_filter_callable(spec)

        prepared_context = _prepare_context_for_docx(context, part=part)

        try:
            doc.render(prepared_context, jinja_env=jinja_env, autoescape=True)
        except TypeError:
            try:
                doc.render(prepared_context, jinja_env=jinja_env)
            except TypeError:
                doc.render(prepared_context)

        file_stream = io.BytesIO()
        doc.save(file_stream)
        file_stream.seek(0)
        return _ensure_editable_bytes(file_stream.read())
    except TemplateError as err:
        raise TemplateRenderError(
            f"DOCX template '{template_filename}' failed: {err}"
        ) from err
    except OSError as err:
        detail = err.strerror or str(err)
        raise TemplateRenderError(
            f"Could not read DOCX template '{template_filename}': {detail}"
        ) from err


render_docx = render
