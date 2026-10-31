"""Microsoft Word OpenXML Mistletoe renderer for QuizML Markdown AST."""

import logging
import re
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import latex2mathml.converter
import mathml2omml
from bs4 import BeautifulSoup
from markupsafe import Markup
from mistletoe.base_renderer import BaseRenderer
from mistletoe.block_token import HTMLBlock

from quizml.exceptions import MarkdownAttributeError
from quizml.markdown.extensions import ImageWithWidth, MathDisplay, MathInline
from quizml.markdown.html_renderer import strip_math_delimiters
from quizml.markdown.image_embedding import convert_css_values_to_pixels
from quizml.markdown.macros import LatexMacroExpander, preprocess_latex_for_mathml
from quizml.paths import find_path

_ALIGNMENT_ENV_RE = re.compile(
    r"\\begin\{(?:align|alignat|flalign|gather|multline|split|aligned)"
)

_TABLE_PROPS_XML = (
    '<w:tblPr><w:tblW w:w="0" w:type="auto"/><w:tblBorders>'
    '<w:top w:val="single" w:sz="6" w:space="0" w:color="B0B0B0"/>'
    '<w:bottom w:val="single" w:sz="6" w:space="0" w:color="B0B0B0"/>'
    '<w:insideH w:val="single" w:sz="4" w:space="0" w:color="D0D0D0"/>'
    '<w:left w:val="none"/><w:right w:val="none"/><w:insideV w:val="none"/>'
    "</w:tblBorders>"
    '<w:tblCellMar><w:top w:w="120" w:type="dxa"/><w:bottom w:w="120" w:type="dxa"/>'
    '<w:left w:w="180" w:type="dxa"/><w:right w:w="180" w:type="dxa"/></w:tblCellMar>'
    "</w:tblPr>"
)


def xml_escape(text: str) -> str:
    """Escape XML special characters (``&``, ``<``, ``>``)."""
    if not text:
        return ""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _add_run_prop(xml_runs: str, prop: str) -> str:
    """Inject a run property tag (e.g. ``<w:b/>``) into all ``<w:r>`` elements."""

    def update_run(m: re.Match[str]) -> str:
        run = m.group(0)
        if "<w:rPr>" in run:
            return run.replace("<w:rPr>", f"<w:rPr>{prop}")
        if "<w:rPr " in run:
            return re.sub(r"(<w:rPr[^>]*>)", r"\1" + prop, run)
        return re.sub(r"(<w:r[^>]*>)", r"\1<w:rPr>" + prop + "</w:rPr>", run)

    return re.sub(r"<w:r[ >].*?</w:r>", update_run, xml_runs, flags=re.DOTALL)


def _extract_omml_row_cells(row: str) -> list[str]:
    """Extract top-level ``<m:e>...</m:e>`` cells from an OMML ``<m:mr>`` row."""
    cells: list[str] = []
    depth = 0
    start = -1
    pos = 0
    row_len = len(row)
    while pos < row_len:
        if row.startswith("<m:e>", pos) or row.startswith("<m:e ", pos):
            if depth == 0:
                start = pos
            depth += 1
            pos += 4
        elif row.startswith("</m:e>", pos):
            depth -= 1
            if depth == 0 and start != -1:
                cells.append(row[start : pos + 6])
                start = -1
            pos += 5
        elif row.startswith("<m:e/>", pos):
            if depth == 0:
                cells.append("<m:e/>")
            pos += 5
        pos += 1
    return cells


def _compute_omml_column_alignments(
    col_cells: list[list[str]], max_cols: int, is_alignment_env: bool
) -> list[str]:
    """Determine ``left``/``center``/``right`` alignment for each OMML column."""
    alignments: list[str] = []
    for c_idx in range(max_cols):
        cells = col_cells[c_idx] if c_idx < len(col_cells) else []
        has_op = any(
            re.search(r"<m:t>\s*(=|&lt;|&gt;|≤|≥|≈|≠|≡|\+|-)", cell) for cell in cells
        )
        has_normal_text = any("<m:nor/>" in cell for cell in cells)

        if c_idx == 0:
            if is_alignment_env or (
                max_cols > 1
                and any(
                    re.search(r"<m:t>\s*(=|&lt;|&gt;|≤|≥|≈|≠|≡)", c)
                    for c in (col_cells[1] if len(col_cells) > 1 else [])
                )
            ):
                alignments.append("right")
            else:
                alignments.append("center")
        elif has_op or has_normal_text:
            alignments.append("left")
        elif is_alignment_env:
            alignments.append("right" if c_idx % 2 == 0 else "left")
        else:
            alignments.append("left" if c_idx % 2 == 1 else "right")
    return alignments


def align_omml_matrices(omml: str, is_alignment_env: bool = False) -> str:
    """Inject ``<m:mPr>`` with column alignment into OMML matrices (``<m:m>``).

    For alignment environments (``align``, ``alignat``, ``split``, etc.) or matrices
    where subsequent columns start with comparison/equality operators, this ensures
    Word renders columns with proper alignment (right-aligned LHS, left-aligned RHS)
    instead of default center justification.
    """
    if "<m:m>" not in omml and "<m:m " not in omml:
        return omml

    def process_matrix(match: re.Match[str]) -> str:
        full_content = match.group(1)
        if "<m:mPr>" in full_content or "<m:mPr " in full_content:
            return match.group(0)

        rows = re.findall(r"<m:mr>(.*?)</m:mr>", full_content, flags=re.DOTALL)
        if not rows:
            return match.group(0)

        max_cols = 0
        col_cells: list[list[str]] = []
        for row in rows:
            cells = _extract_omml_row_cells(row)
            if len(cells) > max_cols:
                max_cols = len(cells)
            for idx, c in enumerate(cells):
                while len(col_cells) <= idx:
                    col_cells.append([])
                col_cells[idx].append(c)

        if max_cols == 0:
            return match.group(0)

        alignments = _compute_omml_column_alignments(
            col_cells, max_cols, is_alignment_env
        )
        mc_elements = "".join(
            f'<m:mc><m:mcPr><m:mcJc m:val="{align}"/>'
            '<m:count m:val="1"/></m:mcPr></m:mc>'
            for align in alignments
        )
        mpr = (
            '<m:mPr><m:baseJc m:val="center"/><m:plcHide m:val="1"/>'
            f"<m:mcs>{mc_elements}</m:mcs></m:mPr>"
        )
        return f"<m:m>{mpr}{full_content}</m:m>"

    return re.sub(r"<m:m>(.*?)</m:m>", process_matrix, omml, flags=re.DOTALL)


class QuizMLYamlDocxRenderer(BaseRenderer):
    """Custom Mistletoe renderer that converts Markdown AST into Word OpenXML."""

    def __init__(
        self,
        base_dir: str | Path | None = None,
        search_dirs: Sequence[str | Path] | None = None,
        preamble: str = "",
    ) -> None:
        super().__init__(MathInline, MathDisplay, ImageWithWidth, HTMLBlock)
        self.base_dir = base_dir
        self.search_dirs: list[str | Path] = list(search_dirs or [])
        self.macro_expander = LatexMacroExpander(preamble) if preamble else None

    def render_document(self, token: Any) -> str:
        return self.render_inner(token)

    def render_raw_text(self, token: Any) -> str:
        text = xml_escape(token.content)
        return f'<w:r><w:t xml:space="preserve">{text}</w:t></w:r>'

    def render_strong(self, token: Any) -> str:
        return _add_run_prop(self.render_inner(token), "<w:b/>")

    def render_emphasis(self, token: Any) -> str:
        return _add_run_prop(self.render_inner(token), "<w:i/>")

    def render_strikethrough(self, token: Any) -> str:
        return _add_run_prop(self.render_inner(token), "<w:strike/>")

    def render_inline_code(self, token: Any) -> str:
        code = token.children[0].content if token.children else ""
        text = xml_escape(code)
        return (
            '<w:r><w:rPr><w:rFonts w:ascii="Consolas" w:hAnsi="Consolas"/>'
            f'<w:sz w:val="21"/></w:rPr><w:t xml:space="preserve">{text}</w:t></w:r>'
        )

    def render_line_break(self, token: Any) -> str:
        if getattr(token, "soft", False):
            return '<w:r><w:t xml:space="preserve"> </w:t></w:r>'
        return "<w:r><w:br/></w:r>"

    def render_link(self, token: Any) -> str:
        return self.render_inner(token)

    def _convert_latex_to_omml(self, raw_latex: str, display: str) -> str:
        """Expand macros, convert LaTeX to MathML, and transform MathML into OMML."""
        clean = strip_math_delimiters(raw_latex)
        is_alignment = bool(_ALIGNMENT_ENV_RE.search(clean))
        expanded = self.macro_expander.expand(clean) if self.macro_expander else clean
        preprocessed = preprocess_latex_for_mathml(expanded)
        mml = latex2mathml.converter.convert(preprocessed, display=display)
        mml = re.sub(r"&(?![a-zA-Z0-9#]+;)", "&amp;", mml)
        omml = mathml2omml.convert(mml)
        return align_omml_matrices(omml, is_alignment_env=is_alignment)

    def render_math_inline(self, token: MathInline) -> str:
        try:
            return self._convert_latex_to_omml(token.content, display="inline")
        except Exception as err:
            logging.debug(
                f"Failed to convert inline math to OMML: {token.content} ({err})"
            )
            escaped = xml_escape(token.content)
            return (
                "<w:r><w:rPr><w:i/></w:rPr>"
                f'<w:t xml:space="preserve">{escaped}</w:t></w:r>'
            )

    def render_math_display(self, token: MathDisplay) -> str:
        try:
            aligned_omml = self._convert_latex_to_omml(token.content, display="block")
            return (
                '<w:p><w:pPr><w:jc w:val="center"/>'
                '<w:spacing w:before="120" w:after="120" '
                'w:line="360" w:lineRule="auto"/>'
                f"</w:pPr><m:oMathPara>{aligned_omml}</m:oMathPara></w:p>"
            )
        except Exception as err:
            logging.debug(
                f"Failed to convert display math to OMML: {token.content} ({err})"
            )
            escaped = xml_escape(token.content)
            return (
                '<w:p><w:pPr><w:jc w:val="center"/></w:pPr>'
                "<w:r><w:rPr><w:i/></w:rPr>"
                f'<w:t xml:space="preserve">{escaped}</w:t></w:r></w:p>'
            )

    def render_paragraph(self, token: Any) -> str:
        inner = self.render_inner(token)
        if not inner.strip():
            return ""
        # Standalone image markers are wrapped in a centered paragraph;
        # QuizML's docx renderer later replaces the marker with a <w:drawing>.
        if inner.strip().startswith("<!--QUIZML_IMG:") and inner.strip().endswith(
            "-->"
        ):
            return (
                '<w:p><w:pPr><w:jc w:val="center"/>'
                '<w:spacing w:before="120" w:after="120"/></w:pPr>'
                f"{inner}</w:p>"
            )
        # Avoid wrapping an already-formed block paragraph (such as display math).
        if inner.strip().startswith("<w:p"):
            return inner
        return (
            '<w:p><w:pPr><w:spacing w:line="360" w:lineRule="auto"/>'
            '<w:rPr><w:rFonts w:ascii="Calibri" w:hAnsi="Calibri"/>'
            '<w:sz w:val="24"/></w:rPr></w:pPr>'
            f"{inner}</w:p>"
        )

    def render_heading(self, token: Any) -> str:
        inner = self.render_inner(token)
        val = f"Heading{token.level}"
        return (
            f'<w:p><w:pPr><w:pStyle w:val="{val}"/>'
            '<w:spacing w:before="240" w:after="120"/>'
            '<w:rPr><w:rFonts w:ascii="Calibri" w:hAnsi="Calibri"/><w:b/></w:rPr>'
            f"</w:pPr>{inner}</w:p>"
        )

    def render_block_code(self, token: Any) -> str:
        code_text = token.children[0].content if token.children else ""
        code_lines = [xml_escape(line) for line in code_text.splitlines()]
        runs = "<w:r><w:br/></w:r>".join(
            '<w:r><w:rPr><w:rFonts w:ascii="Consolas" w:hAnsi="Consolas"/>'
            f'<w:sz w:val="20"/></w:rPr><w:t xml:space="preserve">{line}</w:t></w:r>'
            for line in code_lines
        )
        return (
            '<w:p><w:pPr><w:pBdr><w:left w:val="single" w:sz="12" '
            'w:space="4" w:color="CCCCCC"/></w:pPr>'
            '<w:shd w:val="clear" w:color="auto" w:fill="F5F5F5"/>'
            '<w:spacing w:line="240" w:lineRule="auto"/></w:pPr>'
            f"{runs}</w:p>"
        )

    def render_list(self, token: Any) -> str:
        items: list[str] = []
        is_ordered = getattr(token, "start", None) is not None
        for i, item in enumerate(token.children):
            prefix = f"{i + 1}.  " if is_ordered else "•  "
            item_inner = self.render(item)
            if item_inner.startswith(("<w:p>", "<w:p ")):
                item_inner = re.sub(
                    r"^<w:p[^>]*>(?:<w:pPr>.*?</w:pPr>)?",
                    "",
                    item_inner,
                    flags=re.DOTALL,
                )
                item_inner = re.sub(r"</w:p>$", "", item_inner, flags=re.DOTALL)
            items.append(
                '<w:p><w:pPr><w:ind w:left="720"/>'
                '<w:spacing w:line="300" w:lineRule="auto"/>'
                '<w:rPr><w:rFonts w:ascii="Calibri" w:hAnsi="Calibri"/>'
                '<w:sz w:val="24"/></w:rPr></w:pPr>'
                '<w:r><w:rPr><w:rFonts w:ascii="Calibri" w:hAnsi="Calibri"/>'
                f'<w:b/></w:rPr><w:t xml:space="preserve">{prefix}</w:t></w:r>'
                f"{item_inner}</w:p>"
            )
        return "".join(items)

    def render_list_item(self, token: Any) -> str:
        return self.render_inner(token)

    def render_thematic_break(self, token: Any) -> str:
        return (
            '<w:p><w:pPr><w:pBdr><w:bottom w:val="single" w:sz="6" '
            'w:space="1" w:color="CCCCCC"/></w:pPr>'
            '<w:spacing w:before="120" w:after="120"/></w:pPr></w:p>'
        )

    def render_table(self, token: Any) -> str:
        align_map: dict[int | None, str] = {
            None: "left",
            -1: "left",
            0: "center",
            1: "right",
        }
        alignments = getattr(token.header, "row_align", []) if token.header else []
        col_count = (
            len(token.header.children)
            if token.header
            else (len(token.children[0].children) if token.children else 1)
        )

        grid_cols = "".join("<w:gridCol/>" for _ in range(col_count))
        rows_xml: list[str] = []

        if token.header:
            header_cells: list[str] = []
            for j, cell in enumerate(token.header.children):
                align = align_map.get(
                    alignments[j] if j < len(alignments) else None, "left"
                )
                cell_content = _add_run_prop(self.render_inner(cell), "<w:b/>")
                header_cells.append(
                    '<w:tc><w:tcPr><w:shd w:val="clear" w:color="auto" '
                    'w:fill="EFEFEF"/></w:tcPr>'
                    f'<w:p><w:pPr><w:jc w:val="{align}"/>'
                    '<w:spacing w:after="0" w:line="240" w:lineRule="auto"/></w:pPr>'
                    f"{cell_content}</w:p></w:tc>"
                )
            rows_xml.append(
                f"<w:tr><w:trPr><w:tblHeader/></w:trPr>{''.join(header_cells)}</w:tr>"
            )

        for row in token.children:
            row_cells: list[str] = []
            for j, cell in enumerate(row.children):
                align = align_map.get(
                    alignments[j] if j < len(alignments) else None, "left"
                )
                cell_content = self.render_inner(cell)
                row_cells.append(
                    f'<w:tc><w:p><w:pPr><w:jc w:val="{align}"/>'
                    '<w:spacing w:after="0" w:line="240" w:lineRule="auto"/></w:pPr>'
                    f"{cell_content}</w:p></w:tc>"
                )
            rows_xml.append(f"<w:tr>{''.join(row_cells)}</w:tr>")

        return (
            f"<w:tbl>{_TABLE_PROPS_XML}<w:tblGrid>{grid_cols}</w:tblGrid>"
            f"{''.join(rows_xml)}</w:tbl>"
        )

    def render_table_row(self, token: Any) -> str:
        return self.render_inner(token)

    def render_table_cell(self, token: Any) -> str:
        return self.render_inner(token)

    def _resolve_image_path(self, src: str) -> str:
        dirs = list(self.search_dirs)
        if self.base_dir:
            dirs.append(self.base_dir)
        found = find_path(src, dirs)
        return str(found[0]) if found else src

    def render_image(self, token: Any) -> str:
        resolved = self._resolve_image_path(token.src)
        return f"<!--QUIZML_IMG:{resolved}:4.0-->"

    def render_image_with_width(self, token: ImageWithWidth) -> str:
        resolved = self._resolve_image_path(token.src)
        width_in = 4.0
        if getattr(token, "width", None):
            try:
                px = convert_css_values_to_pixels(token.width.strip())
                width_in = round(px / 96.0, 2)
            except ValueError as err:
                raise MarkdownAttributeError(
                    f"Unsupported image width attribute: {token.width}"
                ) from err
        return f"<!--QUIZML_IMG:{resolved}:{width_in}-->"

    def render_html_block(self, token: Any) -> str:
        soup = BeautifulSoup(token.content, "html.parser")
        tables = soup.find_all("table")
        if not tables:
            return ""

        tbl_elements: list[str] = []
        for table in tables:
            rows = table.find_all("tr")
            if not rows:
                continue
            max_cols = max(len(r.find_all(["th", "td"])) for r in rows)
            grid_cols = "".join("<w:gridCol/>" for _ in range(max_cols))
            rows_xml: list[str] = []
            for r in rows:
                cells = r.find_all(["th", "td"])
                is_header = any(c.name == "th" for c in cells)
                cells_xml: list[str] = []
                for c in cells:
                    cell_text = xml_escape(c.get_text().strip())
                    shd = (
                        '<w:tcPr><w:shd w:val="clear" w:color="auto" '
                        'w:fill="EFEFEF"/></w:tcPr>'
                        if is_header
                        else ""
                    )
                    b_tag = "<w:b/>" if is_header else ""
                    cells_xml.append(
                        f'<w:tc>{shd}<w:p><w:pPr><w:jc w:val="left"/>'
                        '<w:spacing w:after="0" w:line="240" '
                        'w:lineRule="auto"/></w:pPr>'
                        '<w:r><w:rPr><w:rFonts w:ascii="Calibri" w:hAnsi="Calibri"/>'
                        f'{b_tag}</w:rPr><w:t xml:space="preserve">{cell_text}</w:t>'
                        "</w:r></w:p></w:tc>"
                    )
                tr_header = "<w:trPr><w:tblHeader/></w:trPr>" if is_header else ""
                rows_xml.append(f"<w:tr>{tr_header}{''.join(cells_xml)}</w:tr>")

            tbl_elements.append(
                f"<w:tbl>{_TABLE_PROPS_XML}<w:tblGrid>{grid_cols}</w:tblGrid>"
                f"{''.join(rows_xml)}</w:tbl>"
            )
        return "".join(tbl_elements)


def get_docx_dict(
    ast_dict: dict[str, Any],
    opts: dict[str, Any] | None = None,
    base_dir: str | Path | None = None,
    search_dirs: Sequence[str | Path] | None = None,
) -> dict[str, Markup]:
    """Return a mapping of ``{markdown_text: Markup(openxml)}`` for ``ast_dict``."""
    opts = opts or {}
    preamble = opts.get("html_pre", "") + "\n" + opts.get("user_pre", "")
    renderer = QuizMLYamlDocxRenderer(
        base_dir=base_dir, search_dirs=search_dirs, preamble=preamble
    )

    docx_dict: dict[str, Markup] = {}
    with renderer:
        for md_text, doc in ast_dict.items():
            rendered = renderer.render(doc)
            docx_dict[md_text] = Markup(rendered)

    return docx_dict
