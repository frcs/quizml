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

_OMR_ASSETS_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../templates/omr_assets")
)

# Map Unicode OMR bubble characters used in tcd-exam.docx to bundled SVG asset names:
#   ⓪ (U+24EA) -> open_0.svg
#   ①..⑨ (U+2460..U+2468) -> open_1.svg .. open_9.svg
#   Ⓐ..Ⓩ (U+24B6..U+24CF) -> open_A.svg .. open_Z.svg
#   🅐..🅩 (U+1F150..U+1F169) -> checked_A.svg .. checked_Z.svg
_OMR_CHAR_TO_ASSET: dict[str, str] = {"\u24ea": "open_0"}
for _i in range(1, 10):
    _OMR_CHAR_TO_ASSET[chr(0x2460 + _i - 1)] = f"open_{_i}"
for _i in range(26):
    _ch = chr(ord("A") + _i)
    _OMR_CHAR_TO_ASSET[chr(0x24B6 + _i)] = f"open_{_ch}"
    _OMR_CHAR_TO_ASSET[chr(0x1F150 + _i)] = f"checked_{_ch}"

_OMR_CHAR_PATTERN = re.compile(
    "[" + "".join(re.escape(c) for c in _OMR_CHAR_TO_ASSET) + "]"
)


def _embed_omr_bubbles_in_docx(doc_obj) -> None:
    """Replaces Unicode OMR bubble characters in a rendered docx.Document with inline SVG drawings,
    while preserving a zero-size hidden <w:t> containing the Unicode character so paragraph/cell
    .text inspection and accessibility remain intact.
    """
    if doc_obj is None:
        return

    from docx.opc.constants import RELATIONSHIP_TYPE as RT
    from docx.opc.packuri import PackURI
    from docx.opc.part import Part
    from docx.oxml import parse_xml
    from docx.oxml.ns import nsdecls, qn

    main_part = doc_obj.part
    package = main_part.package
    rel_cache: dict[tuple[int, str], str] = {}
    part_cache: dict[str, Part] = {}
    drawing_id_counter = 10000

    def _get_svg_rel_id(target_part, asset_name: str) -> str | None:
        key = (id(target_part), asset_name)
        if key in rel_cache:
            return rel_cache[key]
        svg_path = os.path.join(_OMR_ASSETS_DIR, f"{asset_name}.svg")
        if not os.path.isfile(svg_path):
            return None
        if asset_name not in part_cache:
            with open(svg_path, "rb") as f:
                svg_bytes = f.read()
            pack_uri = PackURI(f"/word/media/omr_{asset_name}.svg")
            part_cache[asset_name] = Part(
                pack_uri, "image/svg+xml", svg_bytes, package
            )
        r_id = target_part.relate_to(part_cache[asset_name], RT.IMAGE)
        rel_cache[key] = r_id
        return r_id

    w_t_tag = qn("w:t")
    w_r_tag = qn("w:r")
    w_rpr_tag = qn("w:rPr")
    w_sz_tag = qn("w:sz")
    w_br_tag = qn("w:br")
    xml_space_attr = "{http://www.w3.org/XML/1998/namespace}space"

    # Default extent: 13.5pt in EMUs (1 pt = 12700 EMU -> 13.5pt = 171450 EMU)
    # This provides a 1em visual cap height consistent with body text
    default_extent_emu = 171450

    def _get_extent_for_run(rpr_el) -> int:
        if rpr_el is not None:
            sz_el = rpr_el.find(w_sz_tag)
            if sz_el is not None and sz_el.attrib.get(qn("w:val")):
                try:
                    val = float(sz_el.attrib[qn("w:val")])
                    # half-points to pt: val / 2. Scale by 1.25 for comfortable bubble size
                    pt = (val / 2.0) * 1.25
                    return round(pt * 12700)
                except ValueError:
                    pass
        return default_extent_emu

    def _make_omr_drawing_element(r_id: str, ch: str, asset_name: str, extent_emu: int):
        nonlocal drawing_id_counter
        drawing_id_counter += 1
        doc_pr_id = drawing_id_counter
        drawing_xml = (
            f"<w:drawing {nsdecls('w', 'wp', 'a', 'pic', 'r')}>"
            f'<wp:inline distT="0" distB="0" distL="0" distR="0">'
            f'<wp:extent cx="{extent_emu}" cy="{extent_emu}"/>'
            f'<wp:effectExtent l="0" t="0" r="0" b="0"/>'
            f'<wp:docPr id="{doc_pr_id}" name="OMR_{asset_name}_{doc_pr_id}" descr="{ch}"/>'
            f"<wp:cNvGraphicFramePr>"
            f'<a:graphicFrameLocks noChangeAspect="1"/>'
            f"</wp:cNvGraphicFramePr>"
            f"<a:graphic>"
            f'<a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">'
            f"<pic:pic>"
            f"<pic:nvPicPr>"
            f'<pic:cNvPr id="{doc_pr_id}" name="omr_{asset_name}.svg" descr="{ch}"/>'
            f"<pic:cNvPicPr/>"
            f"</pic:nvPicPr>"
            f"<pic:blipFill>"
            f'<a:blip r:embed="{r_id}">'
            f"<a:extLst>"
            f'<a:ext uri="{{96DAC541-7B7A-43D3-8B79-37D633B846F1}}">'
            f'<asvg:svgBlip xmlns:asvg="http://schemas.microsoft.com/office/drawing/2016/SVG/main" r:embed="{r_id}"/>'
            f"</a:ext>"
            f"</a:extLst>"
            f"</a:blip>"
            f"<a:stretch><a:fillRect/></a:stretch>"
            f"</pic:blipFill>"
            f"<pic:spPr>"
            f"<a:xfrm>"
            f'<a:off x="0" y="0"/>'
            f'<a:ext cx="{extent_emu}" cy="{extent_emu}"/>'
            f"</a:xfrm>"
            f'<a:prstGeom prst="rect"><a:avLst/></a:prstGeom>'
            f"</pic:spPr>"
            f"</pic:pic>"
            f"</a:graphicData>"
            f"</a:graphic>"
            f"</wp:inline>"
            f"</w:drawing>"
        )
        return parse_xml(drawing_xml)

    def _process_element_tree(root_el, target_part):
        t_elements = [
            el
            for el in root_el.iter(w_t_tag)
            if el.text and _OMR_CHAR_PATTERN.search(el.text)
        ]
        for t_el in t_elements:
            parent_r = t_el.getparent()
            if parent_r is None or parent_r.tag != w_r_tag:
                continue
            parent_p = parent_r.getparent()
            if parent_p is None:
                continue

            r_idx = parent_p.index(parent_r)
            rpr_el = parent_r.find(w_rpr_tag)

            new_runs = []
            for child in list(parent_r):
                if child.tag == w_rpr_tag:
                    continue
                if child.tag == w_t_tag and child.text and _OMR_CHAR_PATTERN.search(child.text):
                    text = child.text
                    parts = _OMR_CHAR_PATTERN.split(text)
                    matches = _OMR_CHAR_PATTERN.findall(text)
                    for idx, segment in enumerate(parts):
                        if segment:
                            seg_r = parse_xml(f"<w:r {nsdecls('w')}/>")
                            if rpr_el is not None:
                                import copy

                                seg_r.append(copy.deepcopy(rpr_el))
                            seg_t = parse_xml(f"<w:t {nsdecls('w')}/>")
                            seg_t.set(xml_space_attr, "preserve")
                            seg_t.text = segment
                            seg_r.append(seg_t)
                            new_runs.append(seg_r)

                        if idx < len(matches):
                            ch = matches[idx]
                            asset_name = _OMR_CHAR_TO_ASSET[ch]
                            r_id = _get_svg_rel_id(target_part, asset_name)
                            if r_id is not None:
                                extent_emu = _get_extent_for_run(rpr_el)
                                draw_r = parse_xml(f"<w:r {nsdecls('w')}/>")
                                draw_r.append(
                                    _make_omr_drawing_element(r_id, ch, asset_name, extent_emu)
                                )
                                new_runs.append(draw_r)
                                hid_r = parse_xml(
                                    f"<w:r {nsdecls('w')}><w:rPr><w:vanish/><w:sz w:val=\"2\"/></w:rPr>"
                                    f"<w:t>{ch}</w:t></w:r>"
                                )
                                new_runs.append(hid_r)
                else:
                    import copy

                    other_r = parse_xml(f"<w:r {nsdecls('w')}/>")
                    if rpr_el is not None and child.tag != w_br_tag:
                        other_r.append(copy.deepcopy(rpr_el))
                    other_r.append(copy.deepcopy(child))
                    new_runs.append(other_r)

            for offset, nr in enumerate(new_runs):
                parent_p.insert(r_idx + offset, nr)
            parent_p.remove(parent_r)

    _process_element_tree(doc_obj.element.body, main_part)



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
                if 'Extension="svg"' not in text:
                    text = text.replace(
                        "</Types>",
                        '<Default Extension="svg" ContentType="image/svg+xml"/></Types>',
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

        if hasattr(doc, "docx") and doc.docx is not None:
            _embed_omr_bubbles_in_docx(doc.docx)

        file_stream = io.BytesIO()
        if hasattr(doc, "docx") and doc.docx is not None:
            doc.docx.save(file_stream)
        else:
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
